"""
CLI Commands for Mekong Recruitment System

This module provides CLI commands following AGENT_RULES_DEVELOPER:
- Database initialization
- Admin user creation
- Sample data loading
- Database reset functionality
"""

import click
import json
import os
from datetime import datetime
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from . import db
from .models import User, Position, Step1Question, Step2Question, Step3Question
from app.utils import log_audit_event

@click.command('init-db')
@with_appcontext
def init_db():
    """
    Initialize database tables.
    
    Creates all database tables and indexes following AGENT_RULES_DEVELOPER:
    - SQLAlchemy ORM for all database operations
    - Proper foreign key constraints
    - Create indexes cho frequently queried fields
    """
    try:
        # Create all tables
        db.create_all()
        
        # Create indexes for frequently queried fields
        click.echo('Creating database indexes...')
        
        # Note: Indexes are defined in models with index=True
        # SQLAlchemy will create them automatically
        
        click.echo('Database initialized successfully!')
        
        # Log the initialization
        log_audit_event(
            user_id=None,
            action='database_initialized',
            resource_type='database',
            resource_id=None,
            details={'timestamp': datetime.utcnow().isoformat()}
        )
        
    except Exception as e:
        click.echo(f'Error initializing database: {e}')
        raise click.Abort()

@click.command('create-admin')
@click.option('--username', prompt='Admin username', help='Admin username')
@click.option('--email', prompt='Admin email', help='Admin email')
@click.option('--password', prompt='Admin password', hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--first-name', prompt='First name', help='First name')
@click.option('--last-name', prompt='Last name', help='Last name')
@click.option('--phone', prompt='Phone number', help='Phone number')
@with_appcontext
def create_admin(username, email, password, first_name, last_name, phone):
    """
    Create admin user with full permissions.
    
    Creates an admin user following AGENT_RULES_DEVELOPER:
    - Password hashing với bcrypt
    - Comprehensive user information
    - Admin role với full permissions
    """
    try:
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            click.echo(f'User {username} already exists!')
            return
        
        if User.query.filter_by(email=email).first():
            click.echo(f'Email {email} already registered!')
            return
        
        # Create admin user
        admin = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role='admin',
            password=password,
            is_active=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        click.echo(f'Admin user {username} created successfully!')
        
        # Log admin creation
        log_audit_event(
            user_id=None,
            action='create_admin_user',
            resource_type='user',
            resource_id=admin.id,
            details={
                'username': username,
                'email': email,
                'role': 'admin'
            }
        )
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating admin user: {e}')
        raise click.Abort()

@click.command('load-sample-data')
@with_appcontext
def load_sample_data():
    """
    Load sample data for development and testing.
    
    Loads sample data following AGENT_RULES_DEVELOPER:
    - Sample positions
    - Sample questions for all steps
    - Sample users for different roles
    """
    try:
        click.echo('Loading sample data...')
        
        # Create sample positions
        positions = [
            {
                'title': 'Lead Software Developer',
                'department': 'engineering',
                'level': 'lead',
                'salary_min': 25000000,
                'salary_max': 35000000,
                'description': 'Lead software development team for IoT and AMR systems',
                'required_skills': json.dumps(['Python', 'Flask', 'SQLAlchemy', 'IoT', 'AMR']),
                'is_active': True
            },
            {
                'title': 'Software Engineer',
                'department': 'engineering',
                'level': 'senior',
                'salary_min': 18000000,
                'salary_max': 25000000,
                'description': 'Develop software solutions for industrial automation',
                'required_skills': json.dumps(['Python', 'JavaScript', 'React', 'Database']),
                'is_active': True
            },
            {
                'title': 'DevOps Engineer',
                'department': 'engineering',
                'level': 'mid',
                'salary_min': 12000000,
                'salary_max': 18000000,
                'description': 'Manage infrastructure and deployment pipelines',
                'required_skills': json.dumps(['Docker', 'Kubernetes', 'AWS', 'CI/CD']),
                'is_active': True
            }
        ]
        
        for pos_data in positions:
            position = Position(**pos_data)
            db.session.add(position)
        
        # Create sample users
        users = [
            {
                'username': 'hr_manager',
                'email': 'hr@mekong.com',
                'first_name': 'HR',
                'last_name': 'Manager',
                'phone': '0901234567',
                'role': 'hr',
                'password': 'hr123456'
            },
            {
                'username': 'interviewer1',
                'email': 'interviewer1@mekong.com',
                'first_name': 'Technical',
                'last_name': 'Interviewer',
                'phone': '0901234568',
                'role': 'interviewer',
                'password': 'interviewer123'
            },
            {
                'username': 'cto',
                'email': 'cto@mekong.com',
                'first_name': 'CTO',
                'last_name': 'Mekong',
                'phone': '0901234569',
                'role': 'executive',
                'password': 'cto123456'
            }
        ]
        
        for user_data in users:
            user = User(**user_data)
            db.session.add(user)
        
        # Load sample questions from JSON files
        load_sample_questions()
        
        db.session.commit()
        click.echo('Sample data loaded successfully!')
        
        # Log sample data loading
        log_audit_event(
            user_id=None,
            action='load_sample_data',
            resource_type='database',
            resource_id=None,
            details={
                'positions_created': len(positions),
                'users_created': len(users),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error loading sample data: {e}')
        raise click.Abort()

def load_sample_questions():
    """
    Load sample questions from JSON files.
    """
    try:
        # Load Step 1 questions
        step1_file = os.path.join('data', 'step1_questions.json')
        if os.path.exists(step1_file):
            with open(step1_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Load IQ questions
            for q in data.get('iq_questions', []):
                question = Step1Question(
                    question_text=q['question'],
                    question_type='iq',
                    category=q['category'],
                    difficulty=q['difficulty'],
                    options=json.dumps(q['options']),
                    correct_answer=q['correct_answer'],
                    explanation=q['explanation'],
                    points=q['points'],
                    is_active=True
                )
                db.session.add(question)
            
            # Load technical questions
            for q in data.get('technical_questions', []):
                question = Step1Question(
                    question_text=q['question'],
                    question_type='technical',
                    category=q['category'],
                    difficulty=q['difficulty'],
                    options=json.dumps(q['options']),
                    correct_answer=q['correct_answer'],
                    explanation=q['explanation'],
                    points=q['points'],
                    is_active=True
                )
                db.session.add(question)
        
        # Load Step 2 questions
        step2_file = os.path.join('data', 'step2_questions.json')
        if os.path.exists(step2_file):
            with open(step2_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Load lead developer questions
            for q in data.get('lead_developer_questions', []):
                question = Step2Question(
                    title=q['title'],
                    content=q['content'],
                    category=q['category'],
                    difficulty=q['difficulty'],
                    time_minutes=q['time_minutes'],
                    evaluation_criteria=json.dumps(q['evaluation_criteria']),
                    related_technologies=json.dumps(q['related_technologies']),
                    is_active=True
                )
                db.session.add(question)
            
            # Load software engineer questions
            for q in data.get('software_engineer_questions', []):
                question = Step2Question(
                    title=q['title'],
                    content=q['content'],
                    category=q['category'],
                    difficulty=q['difficulty'],
                    time_minutes=q['time_minutes'],
                    evaluation_criteria=json.dumps(q['evaluation_criteria']),
                    related_technologies=json.dumps(q['related_technologies']),
                    is_active=True
                )
                db.session.add(question)
        
        # Load Step 3 questions
        step3_file = os.path.join('data', 'step3_questions.json')
        if os.path.exists(step3_file):
            with open(step3_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Load CTO questions
            for q in data.get('cto_questions', []):
                question = Step3Question(
                    title=q['question'],
                    content=q['content'],
                    question_type='cto',
                    category=q['category'],
                    time_minutes=q['time_minutes'],
                    evaluation_criteria=json.dumps(q['evaluation_criteria']),
                    is_active=True
                )
                db.session.add(question)
            
            # Load CEO questions
            for q in data.get('ceo_questions', []):
                question = Step3Question(
                    title=q['question'],
                    content=q['content'],
                    question_type='ceo',
                    category=q['category'],
                    time_minutes=q['time_minutes'],
                    evaluation_criteria=json.dumps(q['evaluation_criteria']),
                    is_active=True
                )
                db.session.add(question)
                
    except Exception as e:
        click.echo(f'Error loading sample questions: {e}')

@click.command('reset-db')
@click.option('--confirm', is_flag=True, help='Confirm database reset')
@with_appcontext
def reset_db(confirm):
    """
    Reset database (drop all tables and recreate).
    
    WARNING: This will delete all data!
    """
    if not confirm:
        click.echo('WARNING: This will delete all data!')
        click.echo('Use --confirm to proceed.')
        return
    
    try:
        click.echo('Dropping all tables...')
        db.drop_all()
        
        click.echo('Recreating tables...')
        db.create_all()
        
        click.echo('Database reset successfully!')
        
        # Log database reset
        log_audit_event(
            user_id=None,
            action='database_reset',
            resource_type='database',
            resource_id=None,
            details={'timestamp': datetime.utcnow().isoformat()}
        )
        
    except Exception as e:
        click.echo(f'Error resetting database: {e}')
        raise click.Abort()

@click.command('create-test-data')
@with_appcontext
def create_test_data():
    """
    Create test data for automated testing.
    """
    try:
        click.echo('Creating test data...')
        
        # Create test positions
        test_positions = [
            {
                'title': 'Test Position',
                'department': 'engineering',
                'level': 'junior',
                'salary_min': 8000000,
                'salary_max': 12000000,
                'description': 'Test position for automated testing',
                'required_skills': json.dumps(['Python', 'Testing']),
                'is_active': True
            }
        ]
        
        for pos_data in test_positions:
            position = Position(**pos_data)
            db.session.add(position)
        
        # Create test users
        test_users = [
            {
                'username': 'test_admin',
                'email': 'test_admin@mekong.com',
                'first_name': 'Test',
                'last_name': 'Admin',
                'phone': '0901234001',
                'role': 'admin',
                'password': 'test123'
            },
            {
                'username': 'test_hr',
                'email': 'test_hr@mekong.com',
                'first_name': 'Test',
                'last_name': 'HR',
                'phone': '0901234002',
                'role': 'hr',
                'password': 'test123'
            }
        ]
        
        for user_data in test_users:
            user = User(**user_data)
            db.session.add(user)
        
        db.session.commit()
        click.echo('Test data created successfully!')
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating test data: {e}')
        raise click.Abort()

@click.command('backup-db')
@click.option('--output', default='backup.json', help='Output file path')
@with_appcontext
def backup_db(output):
    """
    Create database backup.
    """
    try:
        click.echo(f'Creating database backup to {output}...')
        
        # Export all data to JSON
        backup_data = {
            'users': [],
            'positions': [],
            'candidates': [],
            'step1_questions': [],
            'step2_questions': [],
            'step3_questions': [],
            'backup_timestamp': datetime.utcnow().isoformat()
        }
        
        # Export users (without passwords)
        users = User.query.all()
        for user in users:
            backup_data['users'].append({
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None
            })
        
        # Export positions
        positions = Position.query.all()
        for position in positions:
            backup_data['positions'].append({
                'title': position.title,
                'department': position.department,
                'level': position.level,
                'salary_min': position.salary_min,
                'salary_max': position.salary_max,
                'description': position.description,
                'required_skills': position.required_skills,
                'is_active': position.is_active,
                'created_at': position.created_at.isoformat() if position.created_at else None
            })
        
        # Export questions
        step1_questions = Step1Question.query.all()
        for question in step1_questions:
            backup_data['step1_questions'].append({
                'question_text': question.question_text,
                'question_type': question.question_type,
                'category': question.category,
                'difficulty': question.difficulty,
                'options': question.options,
                'correct_answer': question.correct_answer,
                'explanation': question.explanation,
                'points': question.points,
                'is_active': question.is_active
            })
        
        # Write backup file
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        click.echo(f'Database backup created successfully: {output}')
        
        # Log backup creation
        log_audit_event(
            user_id=None,
            action='database_backup',
            resource_type='database',
            resource_id=None,
            details={
                'backup_file': output,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        click.echo(f'Error creating backup: {e}')
        raise click.Abort() 