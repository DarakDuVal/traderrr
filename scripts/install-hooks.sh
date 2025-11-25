#!/bin/bash
# Install git hooks for the project

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/hooks"
GIT_ROOT="$(git rev-parse --show-toplevel)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Installing git hooks...${NC}"

# Check if hooks directory exists
if [ ! -d "$HOOKS_DIR" ]; then
    echo -e "${RED}Error: Hooks directory not found at $HOOKS_DIR${NC}"
    exit 1
fi

# Configure git to use the hooks directory
cd "$GIT_ROOT"
git config core.hooksPath scripts/hooks

# Make hook files executable
chmod +x "$HOOKS_DIR"/*

echo -e "${GREEN}✓ Git hooks installed successfully${NC}"
echo -e "${GREEN}✓ Hooks directory: $HOOKS_DIR${NC}"
echo -e "${GREEN}✓ Git config updated: core.hooksPath = scripts/hooks${NC}"

# Test if black is installed
if ! command -v black &> /dev/null; then
    echo -e "${YELLOW}⚠ Warning: black is not installed${NC}"
    echo -e "${YELLOW}Install it with: pip install black${NC}"
fi

exit 0
