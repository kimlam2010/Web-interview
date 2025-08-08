#!/usr/bin/env python3
"""
WSGI entry point for Mekong Recruitment System
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run() 