#!/usr/bin/env python3
"""
Mekong Recruitment System - Main Application Entry Point

This module serves as the main entry point for the Mekong Recruitment System.
It initializes the Flask application, sets up the database, and starts the development server.

Features:
- Application factory pattern
- Database initialization
- Sample data creation
- Development server configuration
- Error handling and logging
"""

import os
import sys
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models import User, Position, Candidate, Step1Question, Step2Question, Step3Question
from werkzeug.security import generate_password_hash

def create_sample_data():
    """Create sample data for testing."""
    try:
        # Check if sample data already exists
        if Candidate.query.count() > 0:
            print("✅ Sample data already exists")
            return
        
        # Get admin user ID
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("❌ Admin user not found, cannot create sample data")
            return
        
        admin_id = admin.id
        print(f"✅ Using admin user ID: {admin_id}")
        
        # Create sample positions
        positions = [
            Position(
                title="Software Engineer",
                department="Engineering",
                level="Mid-level",
                salary_min=25000000,
                salary_max=35000000,
                description="Full-stack development",
                required_skills="Python, JavaScript, React",
                target_start_date=datetime(2025, 9, 1),
                hiring_urgency="High",
                is_active=True,
                created_by=admin_id
            ),
            Position(
                title="Data Scientist",
                department="Analytics",
                level="Senior",
                salary_min=35000000,
                salary_max=45000000,
                description="Machine learning and data analysis",
                required_skills="Python, SQL, TensorFlow",
                target_start_date=datetime(2025, 10, 1),
                hiring_urgency="Medium",
                is_active=True,
                created_by=admin_id
            )
        ]
        
        for position in positions:
            db.session.add(position)
        db.session.commit()
        
        # Get position IDs for candidates
        position1 = Position.query.filter_by(title="Software Engineer").first()
        position2 = Position.query.filter_by(title="Data Scientist").first()
        
        if not position1 or not position2:
            print("❌ Positions not found, cannot create candidates")
            return
        
        # Create sample candidates
        candidates = [
            Candidate(
                first_name="Nguyễn",
                last_name="Văn A",
                email="nguyenvana@email.com",
                phone="0123456789",
                position_id=position1.id,
                status="pending",
                notes="Good candidate",
                created_by=admin_id
            ),
            Candidate(
                first_name="Trần",
                last_name="Thị B",
                email="tranthib@email.com",
                phone="0987654321",
                position_id=position2.id,
                status="step1_completed",
                notes="Excellent technical skills",
                created_by=admin_id
            )
        ]
        
        for candidate in candidates:
            db.session.add(candidate)
        db.session.commit()
        
        print("✅ Sample data created successfully")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.session.rollback()

def create_admin_user():
    """Create admin user if it doesn't exist."""
    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@mekong.com',
                first_name='Admin',
                last_name='User',
                phone='0123456789',
                role='admin',
                password_hash=generate_password_hash('admin123'),
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created successfully")
        else:
            print("✅ Admin user already exists")
            
        # Verify admin user exists and get its ID
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print(f"✅ Admin user ID: {admin.id}")
        else:
            print("❌ Admin user not found after creation")
            
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.session.rollback()

def initialize_database():
    """Initialize database with tables and sample data."""
    try:
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully")
        
        # Create admin user
        create_admin_user()
        
        # Create sample data
        create_sample_data()
        
        print("✅ Database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

def main():
    """Main application entry point."""
    try:
        # Create Flask application
        app = create_app()
        
        # Initialize database
        with app.app_context():
            initialize_database()
        
        print("🚀 Starting Mekong Recruitment System...")
        print("📱 Access the application at: http://localhost:5000")
        print("👤 Admin login: admin/admin123")
        print("⏹️  Press Ctrl+C to stop the server")
        
        # Run the application
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 