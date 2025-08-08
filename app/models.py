"""
Database Models for Mekong Recruitment System

This module contains all database models following AGENT_RULES_DEVELOPER:
- SQLAlchemy ORM for all database operations
- Proper foreign key constraints
- Indexes for frequently queried fields
- Comprehensive docstrings
- Type hints for all functions
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string
import json

from . import db

class User(UserMixin, db.Model):
    """
    User model for system authentication and role management.
    
    Supports Admin, HR, Interviewer, and Executive roles with
    comprehensive permission system.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='hr', index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_candidates = db.relationship('Candidate', backref='created_by_user', lazy=True)
    interview_evaluations = db.relationship('InterviewEvaluation', backref='interviewer', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    
    def __init__(self, **kwargs):
        """Initialize user with password hashing."""
        if 'password' in kwargs:
            kwargs['password_hash'] = generate_password_hash(kwargs.pop('password'))
        super().__init__(**kwargs)
    
    def set_password(self, password: str) -> None:
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def is_locked(self) -> bool:
        """Check if account is locked due to failed attempts."""
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False
    
    def increment_login_attempts(self) -> None:
        """Increment failed login attempts and lock if necessary."""
        self.login_attempts += 1
        if self.login_attempts >= 3:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def reset_login_attempts(self) -> None:
        """Reset login attempts on successful login."""
        self.login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.utcnow()
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        from .config import USER_ROLES
        role_permissions = USER_ROLES.get(self.role, {})
        return role_permissions.get(permission, False)
    
    def get_full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self) -> str:
        return f'<User {self.username}>'

class Position(db.Model):
    """
    Position model for job management and question assignment.
    
    Supports different levels (junior, mid, senior, lead) with
    position-specific question assignment and scoring configuration.
    """
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, index=True)
    department = db.Column(db.String(50), nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False, index=True)  # junior, mid, senior, lead
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    description = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text)  # JSON array of skills
    target_start_date = db.Column(db.Date)
    hiring_urgency = db.Column(db.Integer, default=3)  # 1-5 scale
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    candidates = db.relationship('Candidate', backref='position', lazy=True)
    step1_questions = db.relationship('PositionStep1Questions', backref='position', lazy=True)
    step2_questions = db.relationship('PositionStep2Questions', backref='position', lazy=True)
    step3_questions = db.relationship('PositionStep3Questions', backref='position', lazy=True)
    
    def __repr__(self) -> str:
        return f'<Position {self.title}>'

class Candidate(db.Model):
    """
    Candidate model for applicant management and progress tracking.
    
    Tracks candidate information, assessment progress, and interview status
    through the 3-step recruitment process.
    """
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, step1_completed, step2_completed, hired, rejected
    cv_filename = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credentials = db.relationship('CandidateCredentials', backref='candidate', uselist=False, lazy=True)
    assessment_results = db.relationship('AssessmentResult', backref='candidate', lazy=True)
    interview_evaluations = db.relationship('InterviewEvaluation', backref='candidate', lazy=True)
    
    def get_full_name(self) -> str:
        """Get candidate's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def get_current_step(self) -> str:
        """Get current step in recruitment process."""
        if self.status == 'pending':
            return 'step1'
        elif self.status == 'step1_completed':
            return 'step2'
        elif self.status == 'step2_completed':
            return 'step3'
        elif self.status == 'hired':
            return 'completed'
        else:
            return 'rejected'
    
    def __repr__(self) -> str:
        return f'<Candidate {self.get_full_name()}>'

class CandidateCredentials(db.Model):
    """
    Temporary credentials model for candidate assessment access.
    
    Provides secure, time-limited access for candidates to complete
    online assessments with automatic expiration and security controls.
    """
    __tablename__ = 'candidate_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    login_attempts = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))  # IPv6 support
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        """Initialize credentials with password hashing."""
        if 'password' in kwargs:
            kwargs['password_hash'] = generate_password_hash(kwargs.pop('password'))
        super().__init__(**kwargs)
    
    def set_password(self, password: str) -> None:
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def is_expired(self) -> bool:
        """Check if credentials have expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_locked(self) -> bool:
        """Check if account is locked due to failed attempts."""
        return self.login_attempts >= 3
    
    def increment_login_attempts(self) -> None:
        """Increment failed login attempts."""
        self.login_attempts += 1
    
    def reset_login_attempts(self) -> None:
        """Reset login attempts on successful login."""
        self.login_attempts = 0
        self.last_login = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f'<CandidateCredentials {self.username}>'

class Step1Question(db.Model):
    """
    Step 1 questions model for online assessment.
    
    Supports IQ and technical questions with auto-scoring capabilities,
    position-specific assignment, and comprehensive metadata.
    """
    __tablename__ = 'step1_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False, index=True)  # iq, technical
    category = db.Column(db.String(50), index=True)  # logical, spatial, programming, etc.
    difficulty = db.Column(db.String(20), index=True)  # easy, medium, hard
    options = db.Column(db.Text)  # JSON array of options
    correct_answer = db.Column(db.String(10), nullable=False)
    explanation = db.Column(db.Text)
    points = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Position-specific assignments
    position_assignments = db.relationship('PositionStep1Questions', backref='question', lazy=True)
    
    def __repr__(self) -> str:
        return f'<Step1Question {self.id}: {self.question_text[:50]}...>'

class Step2Question(db.Model):
    """
    Step 2 questions model for technical interviews.
    
    Supports open-ended questions with manual evaluation,
    position-specific assignment, and evaluation criteria.
    """
    __tablename__ = 'step2_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), index=True)
    difficulty = db.Column(db.String(20), index=True)
    time_minutes = db.Column(db.Integer, default=15)
    evaluation_criteria = db.Column(db.Text)  # JSON array of criteria
    related_technologies = db.Column(db.Text)  # JSON array of technologies
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Position-specific assignments
    position_assignments = db.relationship('PositionStep2Questions', backref='question', lazy=True)
    
    def __repr__(self) -> str:
        return f'<Step2Question {self.id}: {self.title}>'

class Step3Question(db.Model):
    """
    Step 3 Question model for executive interviews (CTO + CEO).
    
    Manages executive-specific questions with difficulty scaling,
    evaluation criteria, and interview structure management.
    """
    __tablename__ = 'step3_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Question Content
    content = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # technical, leadership, cultural, strategic
    category = db.Column(db.String(100), nullable=False)  # system_design, architecture, team_management, etc.
    
    # Executive Assignment
    assigned_to = db.Column(db.String(20), nullable=False)  # cto, ceo, both
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'))
    
    # Difficulty and Time
    difficulty_level = db.Column(db.String(20), nullable=False)  # beginner, intermediate, advanced, expert
    time_allocation = db.Column(db.Integer, default=10)  # minutes
    priority_score = db.Column(db.Integer, default=1)  # 1-10 scale
    
    # Evaluation Criteria
    technical_weight = db.Column(db.Float, default=0.6)  # 0.0-1.0
    leadership_weight = db.Column(db.Float, default=0.2)  # 0.0-1.0
    cultural_weight = db.Column(db.Float, default=0.2)  # 0.0-1.0
    
    # Expected Answers and Scoring
    expected_key_points = db.Column(db.Text)  # JSON array of key points
    scoring_rubric = db.Column(db.Text)  # JSON object with criteria
    sample_answers = db.Column(db.Text)  # JSON array of sample answers
    
    # Usage Statistics
    times_used = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Float, default=0.0)
    success_rate = db.Column(db.Float, default=0.0)  # % of candidates who passed
    
    # Status and Metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    position = db.relationship('Position', backref='step3_question_items')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def get_evaluation_criteria(self) -> Dict[str, float]:
        """Get evaluation criteria weights."""
        return {
            'technical': self.technical_weight,
            'leadership': self.leadership_weight,
            'cultural': self.cultural_weight
        }
    
    def get_expected_points(self) -> List[str]:
        """Get expected key points as list."""
        if self.expected_key_points:
            return json.loads(self.expected_key_points)
        return []
    
    def get_scoring_rubric(self) -> Dict:
        """Get scoring rubric as dictionary."""
        if self.scoring_rubric:
            return json.loads(self.scoring_rubric)
        return {}
    
    def get_sample_answers(self) -> List[str]:
        """Get sample answers as list."""
        if self.sample_answers:
            return json.loads(self.sample_answers)
        return []
    
    def is_for_cto(self) -> bool:
        """Check if question is for CTO."""
        return self.assigned_to in ['cto', 'both']
    
    def is_for_ceo(self) -> bool:
        """Check if question is for CEO."""
        return self.assigned_to in ['ceo', 'both']
    
    def get_difficulty_score(self) -> int:
        """Get numerical difficulty score."""
        difficulty_map = {
            'beginner': 1,
            'intermediate': 2,
            'advanced': 3,
            'expert': 4
        }
        return difficulty_map.get(self.difficulty_level, 1)
    
    def update_usage_stats(self, score: float, passed: bool):
        """Update usage statistics."""
        self.times_used += 1
        
        # Update average score
        total_score = self.average_score * (self.times_used - 1) + score
        self.average_score = total_score / self.times_used
        
        # Update success rate
        if passed:
            passed_count = int(self.success_rate * (self.times_used - 1) / 100) + 1
        else:
            passed_count = int(self.success_rate * (self.times_used - 1) / 100)
        
        self.success_rate = (passed_count / self.times_used) * 100
    
    def __repr__(self) -> str:
        return f'<Step3Question {self.id}: {self.question_type} - {self.assigned_to}>'


class Step3InterviewStructure(db.Model):
    """
    Step 3 Interview Structure model.
    
    Manages the structure and flow of executive interviews
    with question sequences and time allocations.
    """
    __tablename__ = 'step3_interview_structures'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Structure Configuration
    total_duration = db.Column(db.Integer, default=60)  # minutes
    cto_duration = db.Column(db.Integer, default=30)  # minutes
    ceo_duration = db.Column(db.Integer, default=30)  # minutes
    
    # Question Distribution
    cto_questions_count = db.Column(db.Integer, default=3)
    ceo_questions_count = db.Column(db.Integer, default=3)
    
    # Difficulty Distribution
    beginner_ratio = db.Column(db.Float, default=0.2)  # 20%
    intermediate_ratio = db.Column(db.Float, default=0.4)  # 40%
    advanced_ratio = db.Column(db.Float, default=0.3)  # 30%
    expert_ratio = db.Column(db.Float, default=0.1)  # 10%
    
    # Position Assignment
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'))
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    position = db.relationship('Position', backref='step3_structures')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def get_difficulty_distribution(self) -> Dict[str, float]:
        """Get difficulty distribution as dictionary."""
        return {
            'beginner': self.beginner_ratio,
            'intermediate': self.intermediate_ratio,
            'advanced': self.advanced_ratio,
            'expert': self.expert_ratio
        }
    
    def calculate_question_counts(self) -> Dict[str, int]:
        """Calculate question counts by difficulty."""
        total_questions = self.cto_questions_count + self.ceo_questions_count
        
        return {
            'beginner': int(total_questions * self.beginner_ratio),
            'intermediate': int(total_questions * self.intermediate_ratio),
            'advanced': int(total_questions * self.advanced_ratio),
            'expert': int(total_questions * self.expert_ratio)
        }
    
    def __repr__(self) -> str:
        return f'<Step3InterviewStructure {self.name}: {self.total_duration}min>'


class Step3ExecutiveFeedback(db.Model):
    """
    Step 3 Executive Feedback model.
    
    Tracks detailed feedback from CTO and CEO interviews
    with structured evaluation criteria.
    """
    __tablename__ = 'step3_executive_feedbacks'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('step3_questions.id'), nullable=False)
    
    # Executive Information
    executive_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    executive_role = db.Column(db.String(20), nullable=False)  # cto, ceo
    
    # Technical Evaluation
    technical_score = db.Column(db.Float)  # 0-10 scale
    technical_feedback = db.Column(db.Text)
    technical_strengths = db.Column(db.Text)  # JSON array
    technical_weaknesses = db.Column(db.Text)  # JSON array
    
    # Leadership Evaluation
    leadership_score = db.Column(db.Float)  # 0-10 scale
    leadership_feedback = db.Column(db.Text)
    leadership_strengths = db.Column(db.Text)  # JSON array
    leadership_weaknesses = db.Column(db.Text)  # JSON array
    
    # Cultural Evaluation
    cultural_score = db.Column(db.Float)  # 0-10 scale
    cultural_feedback = db.Column(db.Text)
    cultural_fit = db.Column(db.String(20))  # excellent, good, fair, poor
    
    # Overall Assessment
    overall_score = db.Column(db.Float)  # Weighted average
    recommendation = db.Column(db.String(20))  # strong_hire, hire, weak_hire, reject
    detailed_notes = db.Column(db.Text)
    
    # Interview Details
    interview_duration = db.Column(db.Integer)  # minutes
    question_difficulty_rating = db.Column(db.Integer)  # 1-5 scale
    candidate_confidence_rating = db.Column(db.Integer)  # 1-5 scale
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = db.relationship('Candidate', backref='step3_feedbacks')
    question = db.relationship('Step3Question', backref='executive_feedbacks')
    executive = db.relationship('User', foreign_keys=[executive_id])
    
    def calculate_overall_score(self) -> float:
        """Calculate weighted overall score."""
        if all(score is not None for score in [self.technical_score, self.leadership_score, self.cultural_score]):
            weights = self.question.get_evaluation_criteria()
            return (
                self.technical_score * weights['technical'] +
                self.leadership_score * weights['leadership'] +
                self.cultural_score * weights['cultural']
            )
        return 0.0
    
    def get_strengths(self, category: str) -> List[str]:
        """Get strengths for specific category."""
        strengths_map = {
            'technical': self.technical_strengths,
            'leadership': self.leadership_strengths
        }
        strengths_json = strengths_map.get(category)
        if strengths_json:
            return json.loads(strengths_json)
        return []
    
    def get_weaknesses(self, category: str) -> List[str]:
        """Get weaknesses for specific category."""
        weaknesses_map = {
            'technical': self.technical_weaknesses,
            'leadership': self.leadership_weaknesses
        }
        weaknesses_json = weaknesses_map.get(category)
        if weaknesses_json:
            return json.loads(weaknesses_json)
        return []
    
    def get_score_color(self) -> str:
        """Get color class for score display."""
        if self.overall_score >= 8.0:
            return 'success'
        elif self.overall_score >= 6.0:
            return 'warning'
        else:
            return 'danger'
    
    def __repr__(self) -> str:
        return f'<Step3ExecutiveFeedback {self.candidate_id}: {self.executive_role} - {self.overall_score}>'

class AssessmentResult(db.Model):
    """
    Assessment results model for Step 1 auto-scoring.
    
    Tracks detailed scoring breakdown, auto-approval status,
    and manual review requirements.
    """
    __tablename__ = 'assessment_results'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    step = db.Column(db.String(10), nullable=False, index=True)  # step1, step2, step3
    total_score = db.Column(db.Float, nullable=False)
    max_score = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    iq_score = db.Column(db.Float)
    technical_score = db.Column(db.Float)
    answers = db.Column(db.Text)  # JSON array of answers
    time_taken_minutes = db.Column(db.Integer)
    auto_approved = db.Column(db.Boolean, default=False)
    manual_review_required = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_passed(self) -> bool:
        """Check if assessment was passed."""
        return self.percentage >= 70
    
    def requires_manual_review(self) -> bool:
        """Check if manual review is required."""
        return 50 <= self.percentage <= 69
    
    def __repr__(self) -> str:
        return f'<AssessmentResult {self.candidate_id}: {self.percentage}%>'

class InterviewEvaluation(db.Model):
    """
    Interview evaluation model for Step 2 and Step 3.
    
    Tracks manual evaluations with detailed scoring,
    interviewer notes, and approval decisions.
    """
    __tablename__ = 'interview_evaluations'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    step = db.Column(db.String(10), nullable=False, index=True)  # step2, step3
    question_id = db.Column(db.Integer)  # For Step 2 specific questions
    score = db.Column(db.Float, nullable=False)  # 1-10 scale
    notes = db.Column(db.Text)
    recommendation = db.Column(db.String(20))  # approve, reject, review
    evaluation_criteria = db.Column(db.Text)  # JSON array of criteria scores
    interview_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f'<InterviewEvaluation {self.candidate_id}: {self.score}/10>'

class AuditLog(db.Model):
    """
    Audit log model for security tracking.
    
    Records all sensitive operations for compliance
    and security monitoring purposes.
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), index=True)
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # JSON object with action details
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self) -> str:
        return f'<AuditLog {self.action} by {self.user_id}>'

# Position-Question Assignment Tables
class PositionStep1Questions(db.Model):
    """Assignment table for Step 1 questions to positions."""
    __tablename__ = 'position_step1_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('step1_questions.id'), nullable=False)
    is_required = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    
    __table_args__ = (db.UniqueConstraint('position_id', 'question_id'),)

class PositionStep2Questions(db.Model):
    """Assignment table for Step 2 questions to positions."""
    __tablename__ = 'position_step2_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('step2_questions.id'), nullable=False)
    is_required = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    
    __table_args__ = (db.UniqueConstraint('position_id', 'question_id'),)

class PositionStep3Questions(db.Model):
    """Assignment table for Step 3 questions to positions."""
    __tablename__ = 'position_step3_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('step3_questions.id'), nullable=False)
    is_required = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    
    __table_args__ = (db.UniqueConstraint('position_id', 'question_id'),)

class AssessmentLink(db.Model):
    """Assessment links for candidates."""
    __tablename__ = 'assessment_links'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    link_id = db.Column(db.String(16), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, expired, used, deactivated
    custom_message = db.Column(db.Text)
    extension_count = db.Column(db.Integer, default=0)
    last_extended_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    last_extended_at = db.Column(db.DateTime)
    extension_reason = db.Column(db.Text)
    auto_extended = db.Column(db.Boolean, default=False)
    auto_extension_date = db.Column(db.DateTime)
    reminder_24h_sent = db.Column(db.Boolean, default=False)
    reminder_3h_sent = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expired_at = db.Column(db.DateTime)
    deactivated_at = db.Column(db.DateTime)
    deactivated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))
    
    # Relationships
    candidate = db.relationship('Candidate', backref='assessment_links')
    created_by_user = db.relationship('User', foreign_keys=[created_by])
    last_extended_by_user = db.relationship('User', foreign_keys=[last_extended_by])
    deactivated_by_user = db.relationship('User', foreign_keys=[deactivated_by])
    
    def is_expired(self) -> bool:
        """Check if link is expired."""
        return datetime.utcnow() > self.expires_at
    
    def get_remaining_time(self) -> timedelta:
        """Get remaining time until expiry."""
        return self.expires_at - datetime.utcnow()
    
    def get_status_display(self) -> str:
        """Get human-readable status."""
        if self.status == 'active':
            if self.is_expired():
                return 'Expired'
            return 'Active'
        elif self.status == 'used':
            return 'Used'
        elif self.status == 'deactivated':
            return 'Deactivated'
        else:
            return self.status.title()
    
    def __repr__(self) -> str:
        return f'<AssessmentLink {self.link_id}>'


class ExecutiveDecision(db.Model):
    """
    Executive decision model for Step 3 final decisions.
    
    Tracks CTO and CEO decisions with weighted scoring,
    dual approval requirements, and compensation approval workflow.
    """
    __tablename__ = 'executive_decisions'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    
    # CTO Decision
    cto_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    cto_score = db.Column(db.Float)  # Weighted score (technical 60%, cultural 40%)
    cto_recommendation = db.Column(db.String(20))  # hire, reject, review
    cto_notes = db.Column(db.Text)
    cto_evaluated_at = db.Column(db.DateTime)
    
    # CEO Decision
    ceo_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ceo_score = db.Column(db.Float)  # Weighted score (technical 40%, cultural 60%)
    ceo_recommendation = db.Column(db.String(20))  # hire, reject, review
    ceo_notes = db.Column(db.Text)
    ceo_evaluated_at = db.Column(db.DateTime)
    
    # Final Decision
    final_decision = db.Column(db.String(20))  # hire, reject, manual_review
    final_score = db.Column(db.Float)  # Average of CTO and CEO scores
    
    # Compensation Approval
    cto_compensation_approved = db.Column(db.Boolean, default=False)
    ceo_compensation_approved = db.Column(db.Boolean, default=False)
    compensation_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    compensation_approved_at = db.Column(db.DateTime)
    cto_compensation_notes = db.Column(db.Text)
    ceo_compensation_notes = db.Column(db.Text)
    
    # Status and timestamps
    status = db.Column(db.String(20), default='pending', index=True)  # pending, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    candidate = db.relationship('Candidate', backref='executive_decisions')
    cto = db.relationship('User', foreign_keys=[cto_id])
    ceo = db.relationship('User', foreign_keys=[ceo_id])
    
    def is_complete(self) -> bool:
        """Check if both CTO and CEO decisions are complete."""
        return self.cto_id is not None and self.ceo_id is not None
    
    def get_final_score(self) -> float:
        """Calculate final weighted score."""
        if self.cto_score is not None and self.ceo_score is not None:
            return (self.cto_score + self.ceo_score) / 2
        return 0.0
    
    def get_decision_status(self) -> str:
        """Get human-readable decision status."""
        if self.status == 'pending':
            if self.cto_id and not self.ceo_id:
                return 'Waiting for CEO'
            elif self.ceo_id and not self.cto_id:
                return 'Waiting for CTO'
            else:
                return 'Pending'
        elif self.status == 'completed':
            return self.final_decision.title()
        else:
            return self.status.title()
    
    def is_compensation_approved(self) -> bool:
        """Check if compensation is approved by both executives."""
        return self.cto_compensation_approved and self.ceo_compensation_approved
    
    def __repr__(self) -> str:
        return f'<ExecutiveDecision {self.candidate_id}: {self.status}>' 