#!/bin/bash
# Canonical Onboarding Verification Test Runner (Linux/Mac)
# This script runs the canonical onboarding verification tests

echo "===================================="
echo "Canonical Onboarding Verification"
echo "===================================="
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "Error: package.json not found"
    echo "Please run this script from the n8n-ops-ui directory"
    exit 1
fi

echo "Checking for Playwright installation..."
if ! npx playwright --version &> /dev/null; then
    echo "Playwright not found. Installing..."
    npx playwright install
fi

echo ""
echo "Running canonical onboarding verification tests..."
echo ""

# Parse command line arguments
UI_MODE=0
HEADED=0
VERBOSE=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --ui)
            UI_MODE=1
            shift
            ;;
        --headed)
            HEADED=1
            shift
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Build the command
CMD="npx playwright test tests/verification/canonical-onboarding-verification.spec.ts"

if [ $UI_MODE -eq 1 ]; then
    echo "Running in UI mode..."
    CMD="$CMD --ui"
elif [ $HEADED -eq 1 ]; then
    echo "Running in headed mode..."
    CMD="$CMD --headed"
elif [ $VERBOSE -eq 1 ]; then
    echo "Running with verbose output..."
    CMD="$CMD --reporter=list"
fi

echo ""
echo "Executing: $CMD"
echo ""

$CMD

if [ $? -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "VERIFICATION FAILED"
    echo "========================================"
    echo ""
    echo "Some tests failed. Please review the output above."
    echo ""
    echo "To debug:"
    echo "  1. Run with --ui flag to see step-by-step execution"
    echo "  2. Check test-results folder for screenshots"
    echo "  3. Run 'npx playwright show-report' to see HTML report"
    echo ""
    exit 1
else
    echo ""
    echo "========================================"
    echo "VERIFICATION SUCCESSFUL!"
    echo "========================================"
    echo ""
    echo "All canonical onboarding verification tests passed."
    echo "The feature is working correctly."
    echo ""
    exit 0
fi
