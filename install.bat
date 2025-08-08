@echo off
echo ================================
echo  Mekong Recruitment System Setup
echo ================================
echo.

echo Step 1: Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    echo Please ensure Python 3.9+ is installed
    pause
    exit /b 1
)

echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat

echo Step 3: Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo Step 4: Creating directories...
mkdir uploads 2>nul
mkdir exports 2>nul
mkdir exports\reports 2>nul
mkdir exports\step3_questions 2>nul
mkdir static\css 2>nul
mkdir static\js 2>nul
mkdir static\img 2>nul

echo Step 5: Initializing database...
python run.py init-db
if errorlevel 1 (
    echo ERROR: Failed to initialize database
    pause
    exit /b 1
)

echo Step 6: Creating admin user...
python run.py create-admin
if errorlevel 1 (
    echo ERROR: Failed to create admin user
    pause
    exit /b 1
)

echo Step 7: Loading sample data...
python run.py load-sample-data
if errorlevel 1 (
    echo WARNING: Failed to load sample data
    echo You can continue without sample data
)

echo.
echo ================================
echo     INSTALLATION COMPLETE!
echo ================================
echo.
echo Next steps:
echo 1. Run: python run.py
echo 2. Open browser: http://localhost:5000
echo 3. Login with:
echo    Username: admin
echo    Password: admin123
echo.
echo Press any key to start the application...
pause >nul

echo Starting Mekong Recruitment System...
python run.py