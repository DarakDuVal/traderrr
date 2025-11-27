#!/usr/bin/env python3
"""
Setup script to install Git pre-commit hooks.
Run this script after cloning the repository to set up the hooks.

Usage:
    python scripts/setup_hooks.py
    or on Unix: ./scripts/setup_hooks.py
"""

import os
import sys
import shutil
import stat
from pathlib import Path


def setup_pre_commit_hook() -> bool:
    """
    Install the pre-commit hook by copying the script to .git/hooks/

    Returns:
        True if setup was successful, False otherwise
    """
    # Get paths
    repo_root = Path(__file__).parent.parent
    git_hooks_dir = repo_root / ".git" / "hooks"
    hook_script = repo_root / "scripts" / "pre_commit_hook.py"
    hook_target = git_hooks_dir / "pre-commit"

    # Verify hook script exists
    if not hook_script.exists():
        print(f"✗ Error: Hook script not found at {hook_script}")
        return False

    # Ensure .git/hooks directory exists
    git_hooks_dir.mkdir(parents=True, exist_ok=True)

    # Create the hook wrapper
    hook_wrapper_content = '''#!/usr/bin/env python3
"""Pre-commit hook wrapper - executes the cross-platform pre-commit hook script."""

import subprocess
import sys
from pathlib import Path

# Get the repository root and scripts directory
hook_dir = Path(__file__).parent
repo_root = hook_dir.parent.parent
script_path = repo_root / "scripts" / "pre_commit_hook.py"

if not script_path.exists():
    print(f"Error: Pre-commit hook script not found at {script_path}")
    sys.exit(1)

# Execute the pre-commit hook script
result = subprocess.run([sys.executable, str(script_path)])
sys.exit(result.returncode)
'''

    try:
        # Write the hook wrapper
        with open(hook_target, "w") as f:
            f.write(hook_wrapper_content)

        # Make it executable on Unix-like systems
        if sys.platform != "win32":
            st = os.stat(hook_target)
            os.chmod(
                hook_target,
                st.st_mode | stat.S_IEXEC | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
            )

        print(f"[OK] Pre-commit hook installed at {hook_target}")
        return True

    except Exception as e:
        print(f"[ERROR] Error installing pre-commit hook: {e}")
        return False


def verify_dependencies() -> bool:
    """
    Verify that required dependencies are installed.

    Returns:
        True if all dependencies are available, False otherwise
    """
    import subprocess

    required_packages = ["black", "mypy"]
    missing_packages = []

    print("\nVerifying dependencies...")

    for package in required_packages:
        try:
            subprocess.run(
                [sys.executable, "-m", package, "--version"],
                capture_output=True,
                check=True,
            )
            print(f"  [OK] {package} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_packages.append(package)
            print(f"  [MISSING] {package} is not installed")

    if missing_packages:
        print(f"\n[WARNING] Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install -e '.[dev]'")
        return False

    return True


def main() -> int:
    """Main entry point"""
    print("Setting up Git hooks...\n")

    # Setup pre-commit hook
    if not setup_pre_commit_hook():
        return 1

    # Verify dependencies
    if not verify_dependencies():
        print("\n[WARNING] Some dependencies are missing.")
        print("The hook will still work, but type checking will be skipped.")
        print("Install them when ready with: pip install -e '.[dev]'\n")

    print("\n[OK] Git hooks setup complete!")
    print("\nThe pre-commit hook will now automatically:")
    print("  1. Format your code with Black")
    print("  2. Check types with Mypy")
    print("  3. Re-stage any files formatted by Black")
    print("\nYou can still commit if type checks pass.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
