"""
CLI commands for the trading system

Provides administrative commands for:
- Setting up initial admin user
- Managing users
- Database operations
"""

import sys
import logging
import click
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Trading System CLI - Administrative commands"""
    pass


@cli.command()
def setup_admin() -> None:
    """
    Interactive setup for admin user creation

    This command guides you through creating an admin user for the system.
    The admin user can manage other users, API keys, and system settings.
    """
    try:
        from app.db import DatabaseManager
        from app.auth.service import AuthService
        from app.auth.security import validate_password_strength
        from app.models import RoleEnum
        from config.settings import Config

        click.echo("\n" + "=" * 60)
        click.echo("Admin User Setup")
        click.echo("=" * 60 + "\n")

        # Get database session
        try:
            db_manager = DatabaseManager(
                Config.DATABASE_URL or "sqlite:///data/market_data.db"
            )
            session = db_manager.get_session()
        except Exception as e:
            click.echo(f"Error: Could not connect to database: {e}", err=True)
            sys.exit(1)

        try:
            # Check if admin already exists
            from app.auth.init import check_admin_exists

            if check_admin_exists(session):
                click.echo("An admin user already exists. Exiting.")
                return

            # Get username
            while True:
                username = click.prompt("Admin username").strip()
                if not username:
                    click.echo("Username cannot be empty.")
                    continue
                if len(username) < 3:
                    click.echo("Username must be at least 3 characters long.")
                    continue
                break

            # Get email
            while True:
                email = click.prompt("Admin email").strip()
                if not email or "@" not in email:
                    click.echo("Please enter a valid email address.")
                    continue
                break

            # Get password with validation
            while True:
                password = click.prompt("Admin password", hide_input=True)
                is_valid, error_msg = validate_password_strength(password)

                if not is_valid:
                    click.echo(f"Password invalid: {error_msg}")
                    continue

                confirm_password = click.prompt("Confirm password", hide_input=True)
                if password != confirm_password:
                    click.echo("Passwords do not match.")
                    continue

                break

            # Create admin user
            click.echo("\nCreating admin user...")
            success, user, error = AuthService.register_user(
                session, username, email, password, role_name=RoleEnum.ADMIN
            )

            if success:
                click.echo("\n" + "=" * 60)
                click.echo("✓ Admin user created successfully!")
                click.echo("=" * 60)
                click.echo(f"Username: {username}")
                click.echo(f"Email: {email}")
                click.echo(f"Role: admin")
                click.echo("\nYou can now log in with these credentials.")
                click.echo("=" * 60 + "\n")
            else:
                click.echo(f"\nError: {error}", err=True)
                sys.exit(1)

        finally:
            session.close()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("Admin setup failed")
        sys.exit(1)


@cli.command()
def init_db() -> None:
    """
    Initialize the database with schema and default data

    Creates tables and initializes default roles.
    """
    try:
        from app.db import DatabaseManager
        from app.auth.init import ensure_roles_exist
        from config.settings import Config

        click.echo("Initializing database...")

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()

        try:
            # Create all tables
            # Import all models to ensure they're registered with SQLAlchemy
            from app.models import (
                Base,
                User,
                Role,
                Permission,
                APIKey,
                UserAuditLog,
                SystemAuditLog,
                PortfolioPosition,
                SignalHistory,
                PortfolioPerformance,
                DailyData,
                IntradayData,
                Metadata,
                SystemEvent,
            )

            Base.metadata.create_all(db_manager.engine)
            click.echo("✓ Tables created")

            # Initialize default roles
            ensure_roles_exist(session)
            click.echo("✓ Default roles created")

            click.echo("\nDatabase initialized successfully!")

        finally:
            session.close()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("Database initialization failed")
        sys.exit(1)


@cli.command()
@click.option("--username", prompt=True, help="Username to delete")
@click.confirmation_option(
    prompt="Are you sure you want to delete this user? This cannot be undone."
)
def delete_user(username: str) -> None:
    """
    Delete a user from the system

    Use with caution - this operation cannot be undone.
    """
    try:
        from app.db import DatabaseManager
        from app.models import User
        from config.settings import Config

        click.echo(f"Deleting user: {username}")

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()

        try:
            user = session.query(User).filter_by(username=username).first()

            if not user:
                click.echo(f"User '{username}' not found.", err=True)
                sys.exit(1)

            session.delete(user)
            session.commit()
            click.echo(f"✓ User '{username}' deleted successfully")

        finally:
            session.close()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("User deletion failed")
        sys.exit(1)


@cli.command()
def list_users() -> None:
    """
    List all users in the system
    """
    try:
        from app.db import DatabaseManager
        from app.models import User
        from config.settings import Config

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()

        try:
            users = session.query(User).all()

            if not users:
                click.echo("No users found.")
                return

            click.echo("\n" + "=" * 60)
            click.echo("Users")
            click.echo("=" * 60)

            for user in users:
                role_name = user.role.name if user.role else "unknown"
                click.echo(
                    f"ID: {user.id} | Username: {user.username} | "
                    f"Email: {user.email} | Role: {role_name} | Status: {user.status}"
                )

            click.echo("=" * 60 + "\n")

        finally:
            session.close()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("List users failed")
        sys.exit(1)


if __name__ == "__main__":
    cli()
