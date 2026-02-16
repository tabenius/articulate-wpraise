#!/bin/bash
# Secrets Scanner - Scan codebase for hardcoded secrets

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Scanning $PROJECT_ROOT for hardcoded secrets..."
echo ""

FOUND=0

# Patterns to search for
declare -A PATTERNS=(
    ["AWS Access Key"]="AKIA[0-9A-Z]{16}"
    ["Generic API Key"]="api[_-]?key['\"]?\s*[:=]\s*['\"][a-zA-Z0-9]{32,}['\"]"
    ["Private Key"]="-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----"
    ["Generic Secret"]="secret['\"]?\s*[:=]\s*['\"][^'\"]{16,}['\"]"
    ["Password in Code"]="password['\"]?\s*[:=]\s*['\"][^'\"]{8,}['\"]"
    ["Authorization Header"]="Authorization['\"]?\s*:\s*['\"]Bearer [a-zA-Z0-9\-._~+/]+=*['\"]"
    ["Database URL"]="(mysql|postgres|mongodb):\/\/[^:]+:[^@]+@[^\/]+"
    ["Anthropic API Key"]="sk-ant-api03-[a-zA-Z0-9\-_]{95}"
)

# Directories to exclude
EXCLUDE_DIRS=(
    ".git"
    "node_modules"
    ".next"
    "dist"
    "build"
    "__pycache__"
    ".venv"
    "venv"
    ".claude"
    "coverage"
    "tests"
    "test"
    "__tests__"
)

# Build find exclude arguments
EXCLUDE_ARGS=""
for dir in "${EXCLUDE_DIRS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS -path '*/$dir' -prune -o"
done

# Files to exclude
EXCLUDE_FILES=(
    "*.log"
    "*.lock"
    "package-lock.json"
    "*.min.js"
    "*.map"
)

# Scan files
for name in "${!PATTERNS[@]}"; do
    pattern="${PATTERNS[$name]}"

    # Use find with proper exclusions
    results=$(find "$PROJECT_ROOT" $EXCLUDE_ARGS -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" \) -print0 | xargs -0 grep -HnE "$pattern" 2>/dev/null || true)

    if [ ! -z "$results" ]; then
        # Filter out known safe patterns
        results=$(echo "$results" | \
            grep -v ".env.example" | \
            grep -v "your_secure" | \
            grep -v "changeme" | \
            grep -v "placeholder" | \
            grep -v "example.com" | \
            grep -v "localhost" | \
            grep -v "test_password" | \
            grep -v "securepass" | \
            grep -v "/tests/" | \
            grep -v "test_" | \
            grep -v "example_" || true)

        if [ ! -z "$results" ]; then
            echo -e "${RED}❌ $name detected:${NC}"
            echo "$results" | while IFS= read -r line; do
                echo -e "   ${YELLOW}$line${NC}"
            done
            echo ""
            FOUND=1
        fi
    fi
done

# Check for .env files in the repository
env_files=$(git ls-files | grep -E '^\.env$|\.env\.local$' || true)
if [ ! -z "$env_files" ]; then
    echo -e "${RED}❌ .env files in repository:${NC}"
    echo "$env_files" | while IFS= read -r line; do
        echo -e "   ${YELLOW}$line${NC}"
    done
    echo ""
    FOUND=1
fi

if [ $FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ No hardcoded secrets found!${NC}"
    exit 0
else
    echo -e "${RED}🚨 Potential secrets detected. Review the findings above.${NC}"
    echo ""
    echo "Recommendations:"
    echo "  1. Move secrets to .env files (never commit these)"
    echo "  2. Use environment variables"
    echo "  3. Use secret management services (AWS Secrets Manager, Vault)"
    echo "  4. Rotate any exposed credentials immediately"
    echo ""
    exit 1
fi
