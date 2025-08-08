#!/bin/bash

echo "================================"
echo " Mekong Recruitment System Setup"
echo "================================"
echo

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "ERROR: Python 3.9+ is required. Found: $python_version"
    exit 1
fi

echo "Step 1: Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    exit 1
fi

echo "Step 2: Activating virtual environment..."
source venv/bin/activate

echo "Step 3: Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo "Step 4: Creating directories..."
mkdir -p uploads
mkdir -p exports/reports
mkdir -p exports/step3_questions
mkdir -p static/css
mkdir -p static/js
mkdir -p static/img

echo "Step 5: Initializing database..."
python run.py init-db
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to initialize database"
    exit 1
fi

echo "Step 6: Creating admin user..."
python run.py create-admin
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create admin user"
    exit 1
fi

echo "Step 7: Loading sample data..."
python run.py load-sample-data
if [ $? -ne 0 ]; then
    echo "WARNING: Failed to load sample data"
    echo "You can continue without sample data"
fi

echo
echo "================================"
echo "     INSTALLATION COMPLETE!"
echo "================================"
echo
echo "Next steps:"
echo "1. Run: python run.py"
echo "2. Open browser: http://localhost:5000"
echo "3. Login with:"
echo "   Username: admin"
echo "   Password: admin123"
echo
echo "Press Enter to start the application..."
read

echo "Starting Mekong Recruitment System..."
python run.py