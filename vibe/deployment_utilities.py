"""
Deployment Scripts and Database Management Utilities
"""

import os
import sys
import sqlite3
import shutil
import logging
import json
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import zipfile
import requests

# ============================
# IBM Cloud Deployment Manager
# ============================

class IBMCloudDeploymentManager:
    """Manage IBM Cloud deployment and services"""
    
    def __init__(self, project_name: str = "trading-signals"):
        self.project_name = project_name
        self.logger = logging.getLogger(__name__)
        
    def check_prerequisites(self) -> bool:
        """Check if required tools are installed"""
        required_tools = ['ibmcloud', 'docker']
        missing_tools = []
        
        for tool in required_tools:
            try:
                subprocess.run([tool, '--version'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL, 
                             check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing_tools.append(tool)
        
        if missing_tools:
            self.logger.error(f"Missing required tools: {', '.join(missing_tools)}")
            self.logger.info("Please install IBM Cloud CLI and Docker")
            return False
        
        return True
    
    def deploy_to_code_engine(self, 
                            source_path: str = ".",
                            cpu: str = "1",
                            memory: str = "2G",
                            min_scale: int = 1,
                            max_scale: int = 3) -> bool:
        """Deploy application to IBM Cloud Code Engine"""
        
        try:
            if not self.check_prerequisites():
                return False
            
            # Create deployment manifest
            self._create_deployment_manifest(cpu, memory, min_scale, max_scale)
            
            # Build and deploy
            commands = [
                # Login (interactive)
                "echo 'Please login to IBM Cloud manually if not already logged in'",
                
                # Create project if not exists
                f"ibmcloud ce project create --name {self.project_name} || true",
                f"ibmcloud ce project select --name {self.project_name}",
                
                # Create application
                f"ibmcloud ce application create \
                    --name trading-app \
                    --build-source {source_path} \
                    --build-strategy dockerfile \
                    --cpu {cpu} \
                    --memory {memory} \
                    --min-scale {min_scale} \
                    --max-scale {max_scale} \
                    --port 8080 \
                    --env-from-configmap trading-config || \
                ibmcloud ce application update \
                    --name trading-app \
                    --build-source {source_path} \
                    --cpu {cpu} \
                    --memory {memory} \
                    --min-scale {min_scale} \
                    --max-scale {max_scale}"
            ]
            
            for cmd in commands:
                self.logger.info(f"Executing: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.logger.error(f"Command failed: {result.stderr}")
                    return False
                else:
                    self.logger.info(f"Success: {result.stdout}")
            
            # Create services
            self._create_services()
            
            # Get application URL
            app_url = self._get_app_url()
            if app_url:
                self.logger.info(f"Application deployed successfully: {app_url}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            return False
    
    def _create_deployment_manifest(self, cpu: str, memory: str, min_scale: int, max_scale: int):
        """Create deployment configuration"""
        config = {
            "apiVersion": "codeengine.cloud.ibm.com/v1beta1",
            "kind": "Application",
            "metadata": {
                "name": "trading-app"
            },
            "spec": {
                "imageRef": "icr.io/trading-signals/trading-app:latest",
                "resources": {
                    "requests": {
                        "cpu": cpu,
                        "memory": memory
                    }
                },
                "scaling": {
                    "minReplicas": min_scale,
                    "maxReplicas": max_scale
                },
                "env": [
                    {"name": "FLASK_ENV", "value": "production"},
                    {"name": "DATABASE_PATH", "value": "/app/data/market_data.db"},
                    {"name": "MIN_CONFIDENCE", "value": "0.6"}
                ]
            }
        }
        
        with open('deployment.yaml', 'w') as f:
            import yaml
            yaml.dump(config, f)
    
    def _create_services(self):
        """Create required IBM Cloud services"""
        services = [
            {
                "name": "trading-cloudant-db",
                "service": "cloudantnosqldb",
                "plan": "lite"
            },
            {
                "name": "trading-object-storage", 
                "service": "cloud-object-storage",
                "plan": "lite"
            }
        ]
        
        for service in services:
            cmd = f"ibmcloud resource service-instance-create {service['name']} {service['service']} {service['plan']} us-south || true"
            subprocess.run(cmd, shell=True)
            
            # Bind to application
            bind_cmd = f"ibmcloud ce application bind --name trading-app --service-instance {service['name']} || true"
            subprocess.run(bind_cmd, shell=True)
    
    def _get_app_url(self) -> Optional[str]:
        """Get application URL"""
        try:
            result = subprocess.run(
                "ibmcloud ce application get --name trading-app --output json",
                shell=True, capture_output=True, text=True
            )
            
            if result.returncode == 0:
                app_info = json.loads(result.stdout)
                return app_info.get('status', {}).get('url')
        except Exception as e:
            self.logger.error(f"Error getting app URL: {e}")
        
        return None


# ============================
# Database Management Utilities
# ============================

class DatabaseManager:
    """Database management and maintenance utilities"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create database backup"""
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"backup_{timestamp}.db"
        
        try:
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"Database backed up to {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Create backup of current database
            current_backup = self.backup_database(f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            self.logger.info(f"Database restored from {backup_path}")
            self.logger.info(f"Previous database backed up to {current_backup}")
            
            return True
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            return False
    
    def vacuum_database(self) -> bool:
        """Optimize database by running VACUUM"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM")
            conn.close()
            self.logger.info("Database vacuumed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Vacuum failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # Get table sizes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats[f"{table_name}_count"] = count
            
            # Get database size
            stats['database_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
            
            # Get date range for daily_data
            try:
                cursor.execute("SELECT MIN(date), MAX(date) FROM daily_data")
                min_date, max_date = cursor.fetchone()
                stats['date_range'] = f"{min_date} to {max_date}"
            except:
                stats['date_range'] = "No data"
            
            conn.close()
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 730) -> int:
        """Clean up old data"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).date()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clean daily data
            cursor.execute("DELETE FROM daily_data WHERE date < ?", (cutoff_date,))
            daily_deleted = cursor.rowcount
            
            # Clean intraday data (keep less)
            intraday_cutoff = (datetime.now() - timedelta(days=30)).date()
            cursor.execute("DELETE FROM intraday_data WHERE date(datetime) < ?", (intraday_cutoff,))
            intraday_deleted = cursor.rowcount
            
            # Clean old signals
            signal_cutoff = (datetime.now() - timedelta(days=90)).date()
            cursor.execute("DELETE FROM signal_history WHERE date(created_at) < ?", (signal_cutoff,))
            signals_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            total_deleted = daily_deleted + intraday_deleted + signals_deleted
            self.logger.info(f"Cleaned up {total_deleted} old records")
            
            return total_deleted
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return 0
    
    def export_data(self, output_path: str, table_name: str = "daily_data") -> bool:
        """Export data to CSV"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()
            
            df.to_csv(output_path, index=False)
            self.logger.info(f"Data exported to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return False
    
    def import_data(self, csv_path: str, table_name: str = "daily_data") -> bool:
        """Import data from CSV"""
        try:
            df = pd.read_csv(csv_path)
            
            conn = sqlite3.connect(self.db_path)
            df.to_sql(table_name, conn, if_exists='append', index=False)
            conn.close()
            
            self.logger.info(f"Data imported from {csv_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            return False


# ============================
# System Monitor
# ============================

class SystemMonitor:
    """Monitor system health and performance"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_system_health(self) -> Dict:
        """Comprehensive system health check"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        # Database connectivity
        try:
            from data_manager import DataManager
            dm = DataManager()
            dm.close()
            health['checks']['database'] = 'healthy'
        except Exception as e:
            health['checks']['database'] = f'error: {str(e)}'
            health['status'] = 'degraded'
        
        # Disk space
        try:
            disk_usage = shutil.disk_usage('/')
            free_percent = disk_usage.free / disk_usage.total * 100
            health['checks']['disk_space'] = f'{free_percent:.1f}% free'
            
            if free_percent < 10:
                health['status'] = 'critical'
            elif free_percent < 20:
                health['status'] = 'degraded'
        except Exception as e:
            health['checks']['disk_space'] = f'error: {str(e)}'
        
        # Memory usage
        try:
            import psutil
            memory = psutil.virtual_memory()
            health['checks']['memory'] = f'{memory.percent}% used'
            
            if memory.percent > 90:
                health['status'] = 'critical'
            elif memory.percent > 80:
                health['status'] = 'degraded'
        except ImportError:
            health['checks']['memory'] = 'psutil not available'
        except Exception as e:
            health['checks']['memory'] = f'error: {str(e)}'
        
        # Check last signal update
        try:
            # This would need to be implemented based on your signal storage
            health['checks']['last_signal_update'] = 'recent'
        except Exception as e:
            health['checks']['last_signal_update'] = f'error: {str(e)}'
        
        return health
    
    def create_monitoring_dashboard(self) -> str:
        """Create simple monitoring dashboard HTML"""
        health = self.check_system_health()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>System Monitor</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .status-healthy {{ color: green; }}
                .status-degraded {{ color: orange; }}
                .status-critical {{ color: red; }}
                .refresh {{ margin: 10px 0; }}
            </style>
            <script>
                function refreshPage() {{ location.reload(); }}
                setInterval(refreshPage, 30000); // Refresh every 30 seconds
            </script>
        </head>
        <body>
            <h1>System Monitor</h1>
            <p><strong>Status:</strong> <span class="status-{health['status']}">{health['status'].upper()}</span></p>
            <p><strong>Last Check:</strong> {health['timestamp']}</p>
            
            <h2>System Checks</h2>
            <ul>
        """
        
        for check, status in health['checks'].items():
            html += f"<li><strong>{check}:</strong> {status}</li>"
        
        html += """
            </ul>
            
            <div class="refresh">
                <button onclick="refreshPage()">Refresh Now</button>
            </div>
        </body>
        </html>
        """
        
        return html


# ============================
# Alert Manager
# ============================

class AlertManager:
    """Manage alerts and notifications"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def send_email_alert(self, subject: str, message: str) -> bool:
        """Send email alert"""
        if not self.config.get('email_enabled', False):
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.config.get('email_from', 'trading@system.com')
            msg['To'] = self.config.get('email_to', '')
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(self.config.get('smtp_server', 'localhost'), 587)
            server.starttls()
            server.login(self.config.get('email_user', ''), self.config.get('email_pass', ''))
            
            text = msg.as_string()
            server.sendmail(msg['From'], msg['To'], text)
            server.quit()
            
            self.logger.info(f"Email alert sent: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Email alert failed: {e}")
            return False
    
    def send_slack_alert(self, message: str) -> bool:
        """Send Slack alert"""
        if not self.config.get('slack_enabled', False):
            return False
        
        try:
            webhook_url = self.config.get('slack_webhook', '')
            if not webhook_url:
                return False
            
            payload = {
                'text': f"Trading System Alert: {message}",
                'username': 'Trading Bot',
                'icon_emoji': ':chart_with_upwards_trend:'
            }
            
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Slack alert sent: {message}")
            return True
            
        except Exception as e:
            self.logger.error(f"Slack alert failed: {e}")
            return False
    
    def check_and_alert(self, signals: List, portfolio_metrics: Dict):
        """Check conditions and send alerts if needed"""
        try:
            # High confidence signals
            high_confidence_signals = [s for s in signals if s.confidence > 0.8]
            if high_confidence_signals:
                message = f"High confidence signals detected: {len(high_confidence_signals)} signals"
                self.send_email_alert("High Confidence Signals", message)
                self.send_slack_alert(message)
            
            # Risk alerts
            if portfolio_metrics.get('max_drawdown', 0) < -0.2:
                message = "Portfolio drawdown exceeds 20%"
                self.send_email_alert("Risk Alert", message)
                self.send_slack_alert(message)
            
            if portfolio_metrics.get('volatility', 0) > 0.3:
                message = "Portfolio volatility exceeds 30%"
                self.send_email_alert("Volatility Alert", message)
                self.send_slack_alert(message)
                
        except Exception as e:
            self.logger.error(f"Alert check failed: {e}")


# ============================
# Setup and Installation Script
# ============================

def setup_system():
    """Setup the trading system"""
    print("Setting up Trading System...")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher required")
        return False
    
    # Install requirements
    print("Installing Python packages...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✓ Python packages installed")
    except subprocess.CalledProcessError:
        print("✗ Failed to install packages")
        return False
    
    # Initialize database
    print("Initializing database...")
    try:
        from data_manager import DataManager
        dm = DataManager()
        dm.close()
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False
    
    # Create config file
    print("Creating configuration file...")
    try:
        from testing_framework import ConfigManager
        config = ConfigManager()
        config.save_config()
        print("✓ Configuration file created")
    except Exception as e:
        print(f"✗ Configuration creation failed: {e}")
        return False
    
    # Test system
    print("Testing system components...")
    try:
        # Test data manager
        dm = DataManager()
        test_data = dm.get_data_quality_report(['AAPL'])
        dm.close()
        
        # Test indicators
        from indicators import TechnicalIndicators
        ti = TechnicalIndicators()
        
        print("✓ System components working")
    except Exception as e:
        print(f"✗ System test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("\nNext steps:")
    print("1. Review config.json and adjust settings")
    print("2. Run 'python main.py' to start the application")
    print("3. Access dashboard at http://localhost:5000")
    
    return True


# ============================
# Maintenance Scripts
# ============================

def daily_maintenance():
    """Run daily maintenance tasks"""
    print(f"Running daily maintenance - {datetime.now()}")
    
    # Database maintenance
    db_manager = DatabaseManager("market_data.db")
    
    # Backup database
    backup_path = db_manager.backup_database()
    print(f"Database backed up to {backup_path}")
    
    # Clean old data
    deleted_count = db_manager.cleanup_old_data()
    print(f"Cleaned up {deleted_count} old records")
    
    # Vacuum database
    if db_manager.vacuum_database():
        print("Database vacuumed successfully")
    
    # System health check
    monitor = SystemMonitor()
    health = monitor.check_system_health()
    print(f"System status: {health['status']}")
    
    # Send alert if unhealthy
    if health['status'] != 'healthy':
        alert_manager = AlertManager({
            'email_enabled': True,
            'email_to': 'admin@example.com'
        })
        alert_manager.send_email_alert(
            "System Health Alert",
            f"System status: {health['status']}\nDetails: {health['checks']}"
        )


if __name__ == "__main__":
    # Command line interface
    import argparse
    
    parser = argparse.ArgumentParser(description="Trading System Management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup the system')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy to IBM Cloud')
    deploy_parser.add_argument('--cpu', default='1', help='CPU allocation')
    deploy_parser.add_argument('--memory', default='2G', help='Memory allocation')
    
    # Database commands
    db_parser = subparsers.add_parser('database', help='Database operations')
    db_parser.add_argument('action', choices=['backup', 'restore', 'stats', 'cleanup', 'export'])
    db_parser.add_argument('--file', help='File path for backup/restore/export')
    
    # Maintenance command
    maint_parser = subparsers.add_parser('maintenance', help='Run maintenance tasks')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='System monitoring')
    
    args = parser.parse_args()
    
    if args.command == 'setup':
        setup_system()
    
    elif args.command == 'deploy':
        deployer = IBMCloudDeploymentManager()
        deployer.deploy_to_code_engine(cpu=args.cpu, memory=args.memory)
    
    elif args.command == 'database':
        db_manager = DatabaseManager("market_data.db")
        
        if args.action == 'backup':
            backup_path = db_manager.backup_database(args.file)
            print(f"Backup created: {backup_path}")
        
        elif args.action == 'restore':
            if not args.file:
                print("Error: --file required for restore")
            elif db_manager.restore_database(args.file):
                print("Database restored successfully")
        
        elif args.action == 'stats':
            stats = db_manager.get_database_stats()
            print("Database Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        elif args.action == 'cleanup':
            deleted = db_manager.cleanup_old_data()
            print(f"Cleaned up {deleted} records")
        
        elif args.action == 'export':
            if not args.file:
                print("Error: --file required for export")
            elif db_manager.export_data(args.file):
                print(f"Data exported to {args.file}")
    
    elif args.command == 'maintenance':
        daily_maintenance()
    
    elif args.command == 'monitor':
        monitor = SystemMonitor()
        health = monitor.check_system_health()
        print("System Health Check:")
        print(f"Status: {health['status']}")
        print("Checks:")
        for check, status in health['checks'].items():
            print(f"  {check}: {status}")
    
    else:
        parser.print_help()


# Create requirements.txt content
REQUIREMENTS_CONTENT = """Flask==2.3.3
Flask-CORS==4.0.0
pandas==2.0.3
numpy==1.24.3
yfinance==0.2.18
requests==2.31.0
schedule==1.2.0
TA-Lib==0.4.25
urllib3==2.0.4
gunicorn==21.2.0
python-dotenv==1.0.0
cloudant==2.15.0
ibm-cos-sdk==2.13.0
ibm-watson==7.0.1
scipy==1.10.1
psutil==5.9.5
PyYAML==6.0
"""

# Create Dockerfile content
DOCKERFILE_CONTENT = """FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    wget \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \\
    tar -xzf ta-lib-0.4.0-src.tar.gz && \\
    cd ta-lib/ && \\
    ./configure --prefix=/usr && \\
    make && \\
    make install && \\
    cd .. && \\
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory with proper permissions
RUN mkdir -p /app/data && chmod 755 /app/data

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run the application
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "--keepalive", "2"]
"""

# Save additional files
def create_additional_files():
    """Create additional deployment files"""
    
    # Requirements.txt
    with open('requirements.txt', 'w') as f:
        f.write(REQUIREMENTS_CONTENT)
    
    # Dockerfile
    with open('Dockerfile', 'w') as f:
        f.write(DOCKERFILE_CONTENT)
    
    # .dockerignore
    with open('.dockerignore', 'w') as f:
        f.write("""
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis
*.db
backups/
logs/
.DS_Store
""")
    
    # IBM Cloud manifest
    with open('manifest.yml', 'w') as f:
        f.write("""---
applications:
- name: trading-signals-app
  memory: 2G
  instances: 1
  buildpacks:
    - python_buildpack
  command: gunicorn main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  env:
    FLASK_ENV: production
    DATABASE_PATH: /app/data/market_data.db
    MIN_CONFIDENCE: 0.6
    UPDATE_INTERVAL_MINUTES: 30
    BACKUP_ENABLED: true
  services:
    - trading-cloudant-db
    - trading-object-storage
""")
    
    print("Additional deployment files created:")
    print("✓ requirements.txt")
    print("✓ Dockerfile") 
    print("✓ .dockerignore")
    print("✓ manifest.yml")


if __name__ == "__main__":
    create_additional_files()
