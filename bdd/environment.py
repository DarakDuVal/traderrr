"""
BDD Test Environment Setup and Teardown

This module provides configuration and fixtures for Behave BDD tests.
It handles application initialization, test setup, and cleanup.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def before_all(context):
    """
    Setup before running any scenarios.

    This is called once before running all features.
    """
    # Setup logging for BDD tests
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    context.logger = logging.getLogger("bdd.tests")
    context.logger.info("BDD test suite starting...")

    # Store project root for later use
    context.project_root = project_root

    # Initialize test data container
    context.test_data = {}
    context.api_responses = []


def before_scenario(context, scenario):
    """
    Setup before each scenario.

    This is called before running each feature scenario.
    """
    context.logger.info(f"Running scenario: {scenario.name}")

    # Reset test data for each scenario
    context.scenario_data = {}
    context.last_error = None
    context.test_result = None


def after_scenario(context, scenario):
    """
    Cleanup after each scenario.

    This is called after each feature scenario completes.
    """
    status = "PASSED" if scenario.status == "passed" else "FAILED"
    context.logger.info(f"Scenario '{scenario.name}' {status}")

    # Clean up scenario-specific data
    if hasattr(context, "scenario_data"):
        context.scenario_data.clear()


def after_all(context):
    """
    Cleanup after all scenarios.

    This is called after all features have been run.
    """
    context.logger.info("BDD test suite completed")
