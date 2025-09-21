#!/usr/bin/env python3
"""
setup.py - Quick setup script for local development
"""

import os
import sys
import subprocess
import sqlite3


def setup_environment():
    """Setup local development environment"""
    print("Setting up trading system...")

    # Create required directories
    directories = ['data', 'logs', 'backups', 'cache']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

    # Install requirements
    print("Installing Python dependencies...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    print("✓ Dependencies installed")

    # Initialize database
    print("Initializing database...")
    from config.database import DatabaseConfig
    db_config = DatabaseConfig('data/market_data.db')
    if db_config.init_database():
        print("✓ Database initialized")
    else:
        print("✗ Database initialization failed")

    # Create default config if not exists
    if not os.path.exists('config.json'):
        print("Creating default configuration...")
        import json
        from config.settings import Config
        config_data = Config._get_default_config()
        with open('config.json', 'w') as f:
            json.dump(config_data, f, indent=2)
        print("✓ Configuration created")

    print("\n🚀 Setup complete!")
    print("Next steps:")
    print("1. Run tests: python -m pytest tests/")
    print("2. Start application: python main.py")
    print("3. Open browser: http://localhost:5000")


if __name__ == '__main__':
    setup_environment()