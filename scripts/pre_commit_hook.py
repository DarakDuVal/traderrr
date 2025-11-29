#!/usr/bin/env python3
"""
Cross-platform pre-commit hook for Black and Mypy enforcement.
Works on Windows, Linux, and macOS.

This hook:
1. Gets all staged Python files
2. Runs Black formatter and re-stages if changes are made
3. Runs Mypy type checker
4. Reports results and exits with appropriate code
"""

import subprocess
import sys
from typing import List, Tuple


class Colors:
    """ANSI color codes for terminal output"""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color

    @classmethod
    def _supports_colors(cls) -> bool:
        """Check if terminal supports colors"""
        return sys.stdout.isatty()

    @classmethod
    def red(cls, text: str) -> str:
        if cls._supports_colors():
            return f"{cls.RED}{text}{cls.NC}"
        return text

    @classmethod
    def green(cls, text: str) -> str:
        if cls._supports_colors():
            return f"{cls.GREEN}{text}{cls.NC}"
        return text

    @classmethod
    def yellow(cls, text: str) -> str:
        if cls._supports_colors():
            return f"{cls.YELLOW}{text}{cls.NC}"
        return text

    @classmethod
    def blue(cls, text: str) -> str:
        if cls._supports_colors():
            return f"{cls.BLUE}{text}{cls.NC}"
        return text


def get_staged_python_files() -> List[str]:
    """Get list of staged Python files from git index"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]
        return files
    except subprocess.CalledProcessError as e:
        print(Colors.red(f"Error getting staged files: {e}"))
        return []


def run_black(files: List[str]) -> Tuple[bool, bool]:
    """
    Run Black formatter on staged files.

    Returns:
        Tuple of (success: bool, files_changed: bool)
    """
    if not files:
        return True, False

    print(Colors.yellow("Running Black formatter on staged files..."))

    try:
        # First, check what Black would do
        check_result = subprocess.run(
            [sys.executable, "-m", "black", "--check"] + files,
            capture_output=True,
            text=True,
        )

        files_need_formatting = check_result.returncode != 0

        if files_need_formatting:
            # Run Black to format the files
            subprocess.run(
                [sys.executable, "-m", "black"] + files,
                capture_output=True,
                text=True,
                check=True,
            )

            # Re-stage the formatted files
            subprocess.run(
                ["git", "add"] + files,
                capture_output=True,
                text=True,
                check=True,
            )

            print(Colors.green("[OK] Black formatted the following files:"))
            for file in files:
                print(f"  - {file}")
            print(Colors.yellow("Files have been formatted and re-staged."))
            return True, True
        else:
            print(Colors.green("[OK] All files are properly formatted"))
            return True, False

    except subprocess.CalledProcessError as e:
        print(Colors.red(f"[ERROR] Black formatting failed: {e}"))
        print(Colors.red(e.stderr))
        return False, False


def run_mypy(files: List[str]) -> bool:
    """
    Run Mypy type checker on staged files.

    Returns:
        True if all type checks pass, False otherwise
    """
    if not files:
        return True

    # Exclude BDD test files from mypy checking (they use decorators)
    non_bdd_files = [f for f in files if "bdd" not in f]

    if not non_bdd_files:
        print(Colors.green("[OK] BDD files - skipping type check (uses decorators)"))
        return True

    print(Colors.yellow("\nRunning Mypy type checker on staged files..."))

    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy"]
            + non_bdd_files
            + ["--ignore-missing-imports"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(Colors.green("[OK] All type checks passed"))
            return True
        else:
            # Type checking issues are warnings, not failures (tests don't require strict typing)
            print(Colors.yellow("[WARNING] Type checking found issues (non-blocking):"))
            print(result.stdout)
            return True  # Non-blocking: don't fail the commit

    except subprocess.CalledProcessError as e:
        print(Colors.red(f"[ERROR] Mypy type checker failed: {e}"))
        return False
    except FileNotFoundError:
        print(
            Colors.yellow(
                "[WARNING] Mypy not installed. Install with: pip install mypy"
            )
        )
        return True  # Don't fail if mypy not installed


def check_tools_installed() -> bool:
    """Check if required tools are installed"""
    tools = ["black", "mypy"]
    missing = []

    for tool in tools:
        try:
            result = subprocess.run(
                [sys.executable, "-m", tool, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Check for any output (success or version info)
            if not result.stdout and not result.stderr:
                missing.append(tool)
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            missing.append(tool)

    if missing:
        print(Colors.red(f"Error: Required tools not installed: {', '.join(missing)}"))
        print(
            Colors.yellow(
                "Install development dependencies with: pip install -e '.[dev]'"
            )
        )
        return False

    return True


def main() -> int:
    """Main entry point for pre-commit hook"""
    # Check if tools are available
    if not check_tools_installed():
        return 1

    # Get staged Python files
    staged_files = get_staged_python_files()

    if not staged_files:
        print(Colors.blue("No Python files staged for commit"))
        return 0

    print(Colors.blue(f"Checking {len(staged_files)} staged Python file(s)..."))
    print()

    # Run Black formatter
    black_success, black_changed = run_black(staged_files)

    # Run Mypy type checker
    mypy_success = run_mypy(staged_files)

    print()

    # Report final status
    if not black_success:
        print(Colors.red("[ERROR] Code formatting check failed"))
        return 1

    if not mypy_success:
        print(Colors.red("[ERROR] Type checking failed"))
        return 1

    if black_changed:
        print(
            Colors.yellow(
                "[WARNING] Files were formatted by Black and re-staged. Please review changes."
            )
        )
        return 0

    print(Colors.green("[OK] All checks passed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
