@echo off
REM Canonical Onboarding Verification Test Runner (Windows)
REM This script runs the canonical onboarding verification tests

echo ====================================
echo Canonical Onboarding Verification
echo ====================================
echo.

REM Check if we're in the right directory
if not exist "package.json" (
    echo Error: package.json not found
    echo Please run this script from the n8n-ops-ui directory
    pause
    exit /b 1
)

echo Checking for Playwright installation...
npx playwright --version >nul 2>&1
if errorlevel 1 (
    echo Playwright not found. Installing...
    call npx playwright install
)

echo.
echo Running canonical onboarding verification tests...
echo.

REM Parse command line arguments
set UI_MODE=0
set HEADED=0
set VERBOSE=0

:parse_args
if "%1"=="" goto run_tests
if /i "%1"=="--ui" set UI_MODE=1
if /i "%1"=="--headed" set HEADED=1
if /i "%1"=="--verbose" set VERBOSE=1
shift
goto parse_args

:run_tests
REM Build the command
set CMD=npx playwright test tests\verification\canonical-onboarding-verification.spec.ts

if %UI_MODE%==1 (
    echo Running in UI mode...
    set CMD=%CMD% --ui
) else if %HEADED%==1 (
    echo Running in headed mode...
    set CMD=%CMD% --headed
) else if %VERBOSE%==1 (
    echo Running with verbose output...
    set CMD=%CMD% --reporter=list
)

echo.
echo Executing: %CMD%
echo.

%CMD%

if errorlevel 1 (
    echo.
    echo ========================================
    echo VERIFICATION FAILED
    echo ========================================
    echo.
    echo Some tests failed. Please review the output above.
    echo.
    echo To debug:
    echo   1. Run with --ui flag to see step-by-step execution
    echo   2. Check test-results folder for screenshots
    echo   3. Run 'npx playwright show-report' to see HTML report
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo VERIFICATION SUCCESSFUL!
    echo ========================================
    echo.
    echo All canonical onboarding verification tests passed.
    echo The feature is working correctly.
    echo.
    pause
    exit /b 0
)
