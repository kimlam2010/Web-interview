#!/usr/bin/env python3
"""
Mekong Recruitment System - Application Runner

This script starts the Flask application with proper configuration
for development environment.
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import User, Candidate, Position, Step1Question, Step2Question, Step3Question, AssessmentResult, InterviewEvaluation

def init_database():
    """Initialize database with sample data."""
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create admin user if not exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            from werkzeug.security import generate_password_hash
            admin_user = User(
                username='admin',
                email='admin@mekong.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                first_name='Admin',
                last_name='User'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin user created: admin/admin123")
        
        # Create sample positions
        if Position.query.count() == 0:
            positions = [
                Position(
                    title='Software Engineer', 
                    department='Engineering', 
                    level='mid',
                    description='Develop and maintain software applications using modern technologies.'
                ),
                Position(
                    title='Senior Developer', 
                    department='Engineering', 
                    level='senior',
                    description='Lead development projects and mentor junior developers.'
                ),
                Position(
                    title='HR Manager', 
                    department='Human Resources', 
                    level='senior',
                    description='Manage recruitment processes and employee relations.'
                ),
                Position(
                    title='Product Manager', 
                    department='Product', 
                    level='mid',
                    description='Define product strategy and manage product development lifecycle.'
                )
            ]
            db.session.add_all(positions)
            db.session.commit()
            print("✅ Sample positions created")
        
        # Create sample questions
        if Step1Question.query.count() == 0:
            questions = [
                Step1Question(
                    question_text='What comes next in the sequence: 2, 4, 8, 16, ...?',
                    question_type='iq',
                    category='logical',
                    difficulty='medium',
                    options='["20", "24", "32", "30"]',
                    correct_answer='32',
                    is_active=True
                ),
                Step1Question(
                    question_text='What is the time complexity of binary search?',
                    question_type='technical',
                    category='algorithms',
                    difficulty='medium',
                    options='["O(1)", "O(log n)", "O(n)", "O(n²)"]',
                    correct_answer='O(log n)',
                    is_active=True
                ),
                Step1Question(
                    question_text='Which data structure uses LIFO?',
                    question_type='technical',
                    category='programming',
                    difficulty='easy',
                    options='["Queue", "Stack", "Tree", "Graph"]',
                    correct_answer='Stack',
                    is_active=True
                )
            ]
            db.session.add_all(questions)
            db.session.commit()
            print("✅ Sample questions created")
        
        # Create sample positions
        positions = [
            Position(
                title='Software Engineer',
                department='Engineering',
                level='mid',
                description='Develop and maintain software applications using modern technologies.'
            ),
            Position(
                title='Data Scientist',
                department='Analytics',
                level='senior',
                description='Analyze data and build machine learning models.'
            ),
            Position(
                title='Product Manager',
                department='Product',
                level='mid',
                description='Lead product development and strategy.'
            ),
            Position(
                title='UX Designer',
                department='Design',
                level='junior',
                description='Create user-centered design solutions.'
            )
        ]
        
        for position in positions:
            db.session.add(position)
        
        # Create sample candidates
        candidates = [
            Candidate(
                first_name='Nguyễn',
                last_name='Văn A',
                email='nguyenvana@email.com',
                phone='0901234567',
                position_id=1,
                status='pending'
            ),
            Candidate(
                first_name='Trần',
                last_name='Thị B',
                email='tranthib@email.com',
                phone='0901234568',
                position_id=2,
                status='step1_completed'
            ),
            Candidate(
                first_name='Lê',
                last_name='Văn C',
                email='levanc@email.com',
                phone='0901234569',
                position_id=1,
                status='step2_completed'
            ),
            Candidate(
                first_name='Phạm',
                last_name='Thị D',
                email='phamthid@email.com',
                phone='0901234570',
                position_id=3,
                status='hired'
            ),
            Candidate(
                first_name='Hoàng',
                last_name='Văn E',
                email='hoangvane@email.com',
                phone='0901234571',
                position_id=4,
                status='rejected'
            )
        ]
        
        for candidate in candidates:
            db.session.add(candidate)
        
        # Create sample assessment results
        assessment_results = [
            AssessmentResult(
                candidate_id=2,
                step='step1',
                total_score=85,
                max_score=100,
                percentage=85,
                iq_score=40,
                technical_score=45,
                auto_approved=True,
                manual_review_required=False,
                completed_at=datetime.utcnow() - timedelta(days=2)
            ),
            AssessmentResult(
                candidate_id=3,
                step='step1',
                total_score=92,
                max_score=100,
                percentage=92,
                iq_score=45,
                technical_score=47,
                auto_approved=True,
                manual_review_required=False,
                completed_at=datetime.utcnow() - timedelta(days=1)
            ),
            AssessmentResult(
                candidate_id=4,
                step='step1',
                total_score=78,
                max_score=100,
                percentage=78,
                iq_score=38,
                technical_score=40,
                auto_approved=True,
                manual_review_required=False,
                completed_at=datetime.utcnow() - timedelta(days=3)
            ),
            AssessmentResult(
                candidate_id=5,
                step='step1',
                total_score=45,
                max_score=100,
                percentage=45,
                iq_score=20,
                technical_score=25,
                auto_approved=False,
                manual_review_required=True,
                completed_at=datetime.utcnow() - timedelta(days=4)
            )
        ]
        
        for result in assessment_results:
            db.session.add(result)

        print("✅ Database initialized successfully!")

def main():
    """Main application entry point."""
    app = create_app()
    
    # Initialize database
    with app.app_context():
        init_database()
    
    # Run the application
    print("🚀 Starting Mekong Recruitment System...")
    print("📱 Access the application at: http://localhost:5000")
    print("👤 Admin login: admin/admin123")
    print("⏹️  Press Ctrl+C to stop the server")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )

if __name__ == '__main__':
    main()