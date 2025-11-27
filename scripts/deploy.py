#!/usr/bin/env python3
"""
scripts/deploy.py
Automated deployment script for IBM Cloud Code Engine
"""

import sys
import subprocess
import json
import time
import argparse
import logging


class IBMCloudDeployer:
    """IBM Cloud Code Engine deployment automation"""

    def __init__(self, project_name: str = "trading-signals"):
        self.project_name = project_name
        self.app_name = "traderrr"
        self.logger = self._setup_logging()

    def _setup_logging(self):
        """Setup logging"""
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        return logging.getLogger(__name__)

    def check_prerequisites(self) -> bool:
        """Check if required tools are installed"""
        self.logger.info("Checking prerequisites...")

        # Check IBM Cloud CLI
        try:
            result = subprocess.run(["ibmcloud", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(
                    "IBM Cloud CLI not found. Install from: https://cloud.ibm.com/docs/cli"
                )
                return False
            self.logger.info(f"IBM Cloud CLI: {result.stdout.strip()}")
        except FileNotFoundError:
            self.logger.error(
                "IBM Cloud CLI not found. Install from: https://cloud.ibm.com/docs/cli"
            )
            return False

        # Check Code Engine plugin
        try:
            result = subprocess.run(["ibmcloud", "plugin", "list"], capture_output=True, text=True)
            if "code-engine" not in result.stdout:
                self.logger.info("Installing Code Engine plugin...")
                subprocess.run(["ibmcloud", "plugin", "install", "code-engine", "-f"])
        except Exception as e:
            self.logger.error(f"Failed to check/install Code Engine plugin: {e}")
            return False

        # Check Docker
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error("Docker not found. Install from: https://docker.com")
                return False
            self.logger.info(f"Docker: {result.stdout.strip()}")
        except FileNotFoundError:
            self.logger.error("Docker not found. Install from: https://docker.com")
            return False

        return True

    def login_ibm_cloud(self, api_key: str = None) -> bool:
        """Login to IBM Cloud"""
        self.logger.info("Logging into IBM Cloud...")

        try:
            if api_key:
                cmd = ["ibmcloud", "login", "--apikey", api_key]
            else:
                cmd = ["ibmcloud", "login", "--sso"]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"IBM Cloud login failed: {result.stderr}")
                return False

            self.logger.info("Successfully logged into IBM Cloud")
            return True

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def create_project(self) -> bool:
        """Create or select Code Engine project"""
        self.logger.info(f"Setting up Code Engine project: {self.project_name}")

        try:
            # Check if project exists
            result = subprocess.run(
                ["ibmcloud", "ce", "project", "get", "--name", self.project_name],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.logger.info(f"Project {self.project_name} already exists")
            else:
                # Create new project
                self.logger.info(f"Creating new project: {self.project_name}")
                result = subprocess.run(
                    [
                        "ibmcloud",
                        "ce",
                        "project",
                        "create",
                        "--name",
                        self.project_name,
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.logger.error(f"Failed to create project: {result.stderr}")
                    return False

            # Select project
            result = subprocess.run(
                ["ibmcloud", "ce", "project", "select", "--name", self.project_name],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.logger.error(f"Failed to select project: {result.stderr}")
                return False

            self.logger.info(f"Project {self.project_name} is ready")
            return True

        except Exception as e:
            self.logger.error(f"Project setup failed: {e}")
            return False

    def build_and_push_image(self, registry_namespace: str) -> str:
        """Build and push Docker image to IBM Container Registry"""
        image_name = f"icr.io/{registry_namespace}/{self.app_name}:latest"

        self.logger.info("Building Docker image...")

        try:
            # Build image
            result = subprocess.run(
                ["docker", "build", "-t", image_name, "."],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.logger.error(f"Docker build failed: {result.stderr}")
                return None

            self.logger.info("Docker image built successfully")

            # Login to IBM Container Registry
            subprocess.run(["ibmcloud", "cr", "login"])

            # Push image
            self.logger.info("Pushing image to IBM Container Registry...")
            result = subprocess.run(["docker", "push", image_name], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Docker push failed: {result.stderr}")
                return None

            self.logger.info(f"Image pushed successfully: {image_name}")
            return image_name

        except Exception as e:
            self.logger.error(f"Image build/push failed: {e}")
            return None

    def deploy_application(
        self,
        image_name: str = None,
        cpu: str = "1",
        memory: str = "2G",
        min_scale: int = 1,
        max_scale: int = 3,
    ) -> bool:
        """Deploy application to Code Engine"""
        self.logger.info(f"Deploying application: {self.app_name}")

        try:
            # Check if app exists
            result = subprocess.run(
                ["ibmcloud", "ce", "application", "get", "--name", self.app_name],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # Update existing app
                cmd = [
                    "ibmcloud",
                    "ce",
                    "application",
                    "update",
                    "--name",
                    self.app_name,
                ]
            else:
                # Create new app
                cmd = [
                    "ibmcloud",
                    "ce",
                    "application",
                    "create",
                    "--name",
                    self.app_name,
                ]

            # Add deployment parameters
            if image_name:
                cmd.extend(["--image", image_name])
            else:
                # Use build source if no image provided
                cmd.extend(["--build-source", ".", "--build-strategy", "dockerfile"])

            cmd.extend(
                [
                    "--cpu",
                    cpu,
                    "--memory",
                    memory,
                    "--min-scale",
                    str(min_scale),
                    "--max-scale",
                    str(max_scale),
                    "--port",
                    "8080",
                    "--env-from-configmap",
                    "trading-config",
                    "--env-from-secret",
                    "trading-secrets",
                ]
            )

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Application deployment failed: {result.stderr}")
                return False

            self.logger.info("Application deployed successfully")

            # Get application URL
            time.sleep(10)  # Wait for deployment
            result = subprocess.run(
                [
                    "ibmcloud",
                    "ce",
                    "application",
                    "get",
                    "--name",
                    self.app_name,
                    "--output",
                    "json",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                app_info = json.loads(result.stdout)
                url = app_info.get("status", {}).get("url")
                if url:
                    self.logger.info(f"Application URL: {url}")
                    self.logger.info(f"Health check: {url}/api/health")

            return True

        except Exception as e:
            self.logger.error(f"Application deployment failed: {e}")
            return False

    def create_config_resources(self) -> bool:
        """Create ConfigMap and Secrets for application"""
        self.logger.info("Creating configuration resources...")

        try:
            # Create ConfigMap
            config_vars = {
                "DATABASE_PATH": "/app/data/market_data.db",
                "MIN_CONFIDENCE": "0.6",
                "UPDATE_INTERVAL_MINUTES": "30",
                "BACKUP_ENABLED": "true",
                "FLASK_ENV": "production",
            }

            cmd = ["ibmcloud", "ce", "configmap", "create", "--name", "trading-config"]
            for key, value in config_vars.items():
                cmd.extend(["--from-literal", f"{key}={value}"])

            subprocess.run(cmd, capture_output=True)

            # Create Secret (placeholder - user should add real secrets)
            secret_cmd = [
                "ibmcloud",
                "ce",
                "secret",
                "create",
                "--name",
                "trading-secrets",
                "--from-literal",
                "SECRET_KEY=change-this-in-production",
            ]
            subprocess.run(secret_cmd, capture_output=True)

            self.logger.info("Configuration resources created")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create config resources: {e}")
            return False

    def create_services(self) -> bool:
        """Create IBM Cloud services (Cloudant, Object Storage)"""
        self.logger.info("Creating IBM Cloud services...")

        try:
            # Create Cloudant database
            result = subprocess.run(
                [
                    "ibmcloud",
                    "resource",
                    "service-instance-create",
                    "trading-cloudant-db",
                    "cloudantnosqldb",
                    "lite",
                    "us-south",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0 and "already exists" not in result.stderr:
                self.logger.warning(f"Cloudant creation failed: {result.stderr}")

            # Create Object Storage
            result = subprocess.run(
                [
                    "ibmcloud",
                    "resource",
                    "service-instance-create",
                    "trading-object-storage",
                    "cloud-object-storage",
                    "lite",
                    "global",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0 and "already exists" not in result.stderr:
                self.logger.warning(f"Object Storage creation failed: {result.stderr}")

            self.logger.info("Services creation completed")
            return True

        except Exception as e:
            self.logger.error(f"Service creation failed: {e}")
            return False

    def bind_services(self) -> bool:
        """Bind services to the application"""
        self.logger.info("Binding services to application...")

        try:
            # Bind Cloudant
            subprocess.run(
                [
                    "ibmcloud",
                    "ce",
                    "application",
                    "bind",
                    "--name",
                    self.app_name,
                    "--service-instance",
                    "trading-cloudant-db",
                ],
                capture_output=True,
            )

            # Bind Object Storage
            subprocess.run(
                [
                    "ibmcloud",
                    "ce",
                    "application",
                    "bind",
                    "--name",
                    self.app_name,
                    "--service-instance",
                    "trading-object-storage",
                ],
                capture_output=True,
            )

            self.logger.info("Services bound successfully")
            return True

        except Exception as e:
            self.logger.error(f"Service binding failed: {e}")
            return False

    def run_health_check(self) -> bool:
        """Run health check on deployed application"""
        self.logger.info("Running health check...")

        try:
            # Get application URL
            result = subprocess.run(
                [
                    "ibmcloud",
                    "ce",
                    "application",
                    "get",
                    "--name",
                    self.app_name,
                    "--output",
                    "json",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self.logger.error("Failed to get application info")
                return False

            app_info = json.loads(result.stdout)
            url = app_info.get("status", {}).get("url")

            if not url:
                self.logger.error("Application URL not found")
                return False

            # Test health endpoint
            import requests

            health_url = f"{url}/api/health"

            for attempt in range(5):
                try:
                    response = requests.get(health_url, timeout=30)
                    if response.status_code == 200:
                        health_data = response.json()
                        self.logger.info(f"Health check passed: {health_data.get('status')}")
                        return True
                    else:
                        self.logger.warning(
                            f"Health check attempt {attempt + 1} failed: {response.status_code}"
                        )
                except requests.RequestException as e:
                    self.logger.warning(f"Health check attempt {attempt + 1} failed: {e}")

                time.sleep(10)

            self.logger.error("Health check failed after 5 attempts")
            return False

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def full_deployment(
        self,
        registry_namespace: str,
        api_key: str = None,
        cpu: str = "1",
        memory: str = "2G",
    ) -> bool:
        """Run complete deployment process"""
        self.logger.info("Starting full deployment process...")

        # Check prerequisites
        if not self.check_prerequisites():
            return False

        # Login
        if not self.login_ibm_cloud(api_key):
            return False

        # Create project
        if not self.create_project():
            return False

        # Create services
        self.create_services()

        # Create config resources
        if not self.create_config_resources():
            return False

        # Build and push image
        image_name = self.build_and_push_image(registry_namespace)

        # Deploy application (use source build if image push failed)
        if not self.deploy_application(image_name, cpu, memory):
            return False

        # Bind services
        self.bind_services()

        # Health check
        if not self.run_health_check():
            self.logger.warning("Deployment succeeded but health check failed")

        self.logger.info("=== DEPLOYMENT COMPLETE ===")
        self.logger.info(f"Project: {self.project_name}")
        self.logger.info(f"Application: {self.app_name}")
        self.logger.info("Next steps:")
        self.logger.info("1. Check application logs: ibmcloud ce application logs --name traderrr")
        self.logger.info("2. Monitor application: ibmcloud ce application get --name traderrr")
        self.logger.info("3. Update configuration as needed")

        return True


def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="Deploy trading system to IBM Cloud")
    parser.add_argument(
        "--project-name", default="trading-signals", help="Code Engine project name"
    )
    parser.add_argument(
        "--registry-namespace", required=True, help="IBM Container Registry namespace"
    )
    parser.add_argument("--api-key", help="IBM Cloud API key (or use --sso for SSO login)")
    parser.add_argument("--cpu", default="1", help="CPU allocation (0.25, 0.5, 1, 2, 4)")
    parser.add_argument("--memory", default="2G", help="Memory allocation (0.5G, 1G, 2G, 4G, 8G)")
    parser.add_argument("--dry-run", action="store_true", help="Check prerequisites only")

    args = parser.parse_args()

    deployer = IBMCloudDeployer(args.project_name)

    if args.dry_run:
        success = deployer.check_prerequisites()
        print("Prerequisites check:", "PASSED" if success else "FAILED")
        return 0 if success else 1

    success = deployer.full_deployment(
        registry_namespace=args.registry_namespace,
        api_key=args.api_key,
        cpu=args.cpu,
        memory=args.memory,
    )

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
