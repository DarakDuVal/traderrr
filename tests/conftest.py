"""
tests/conftest.py
Pytest configuration and fixtures
"""

import warnings
import pytest
import sys


def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Suppress ResourceWarnings from third-party libraries
    # These are not issues in our code but in library internals (pandas, werkzeug, etc.)
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)

    # Suppress warnings at interpreter level
    import os

    os.environ["PYTHONWARNINGS"] = "ignore::ResourceWarning"

    # Add filters to pytest's warning list to suppress resource warnings
    # This ensures warnings don't get collected by pytest
    config.addinivalue_line("filterwarnings", "ignore::ResourceWarning")
    config.addinivalue_line("filterwarnings", "ignore::DeprecationWarning")
    config.addinivalue_line("filterwarnings", "ignore::FutureWarning")


def pytest_collection_modifyitems(config, items):
    """Modify test items to ensure proper warning filtering"""
    for item in items:
        item.add_marker(pytest.mark.filterwarnings("ignore::ResourceWarning"))


# Override Python's default unraisable exception hook to ignore ResourceWarning
_original_hook = sys.unraisablehook


def custom_unraisable_hook(unraisable_msg):
    """Custom hook that ignores ResourceWarning unraisable exceptions"""
    if "unclosed database" not in str(unraisable_msg.exc_value):
        _original_hook(unraisable_msg)


sys.unraisablehook = custom_unraisable_hook
