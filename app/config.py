"""
Configuration System for Mekong Recruitment System

This module provides environment-specific configurations following AGENT_RULES_DEVELOPER:
- Environment variables support
- Security settings with proper defaults
- Database configuration for different environments
- Assessment settings and thresholds
- User roles and permissions matrix
"""

import os
from datetime import timedelta
from typing import Dict, Any

class Config:
    """
    Base configuration class with common settings.
    
    Provides default configuration values and environment-specific
    overrides for development, testing, and production.
    """
    
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mekong-recruitment-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///recruitment.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
    
    # Assessment Settings
    STEP1_TIME_LIMIT = 30 * 60  # 30 minutes in seconds
    STEP1_PASS_THRESHOLD = 70   # 70% to pass Step 1
    STEP2_PASS_THRESHOLD = 70   # 70% to pass Step 2
    
    # Question Settings
    STEP1_IQ_QUESTIONS = 10     # Number of IQ questions
    STEP1_TECH_QUESTIONS = 15   # Number of technical questions
    STEP2_QUESTIONS_PER_SECTION = 4  # Questions per interview section
    
    # Scoring Weights
    STEP1_IQ_WEIGHT = 0.4      # 40% weight for IQ
    STEP1_TECH_WEIGHT = 0.6    # 60% weight for Technical
    
    # Email Settings (Optional)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    DEFAULT_MAIL_SENDER = os.environ.get('DEFAULT_MAIL_SENDER') or 'hr@mekong.com'
    
    # Pagination
    CANDIDATES_PER_PAGE = 20
    
    # Export Settings
    EXPORT_FOLDER = 'exports'
    REPORTS_FOLDER = 'exports/reports'
    STEP3_EXPORT_FOLDER = 'exports/step3_questions'
    
    # Link Management Settings
    LINK_EXPIRATION_DAYS = {
        'step1_default': 7,      # Default 7 days for Step 1
        'step2_default': 3,      # Default 3 days for Step 2
        'step1_max': 30,         # Maximum extension for Step 1
        'step2_max': 14          # Maximum extension for Step 2
    }
    
    # Auto-reminder Settings
    REMINDER_SCHEDULE = {
        'step1_reminder_hours': [24, 3],    # Send reminders 24h and 3h before expiry
        'step2_reminder_hours': [24, 6],    # Send reminders 24h and 6h before expiry
        'weekend_auto_extend': True         # Auto-extend if expires on weekend
    }
    
    # User Role Permissions
    USER_ROLES = {
        'admin': {
            'manage_questions': True,
            'manage_users': True,
            'system_config': True,
            'view_all_candidates': True,
            'delete_candidates': True,
            'extend_links': True,
            'export_data': True,
            'override_any_decision': True,
            'approve_step1_manual': True,
            'approve_step2_override': True,
            'approve_step3_final': True,
            'manage_credentials': True,
            'view_audit_logs': True
        },
        'hr': {
            'manage_questions': False,
            'manage_users': False,
            'system_config': False,
            'view_all_candidates': True,
            'delete_candidates': False,
            'extend_links': True,
            'export_data': True,
            'add_candidates': True,
            'schedule_interviews': True,
            'view_reports': True,
            'generate_credentials': True,
            'manual_review_step1': True,
            'coordinate_interviews': True,
            'view_candidate_credentials': True
        },
        'interviewer': {
            'manage_questions': False,
            'manage_users': False,
            'system_config': False,
            'view_all_candidates': False,
            'delete_candidates': False,
            'extend_links': False,
            'export_data': False,
            'evaluate_step2': True,
            'approve_step2': True,
            'view_assigned_candidates': True,
            'provide_technical_recommendation': True,
            'score_technical_interview': True
        },
        'executive': {
            'manage_questions': False,
            'manage_users': False,
            'system_config': False,
            'view_all_candidates': True,
            'delete_candidates': False,
            'extend_links': False,
            'export_data': True,
            'conduct_step3': True,
            'approve_final_hiring': True,
            'approve_compensation': True,
            'view_hiring_analytics': True,
            'override_technical_decisions': True
        }
    }
    
    # Company Settings
    COMPANY_NAME = 'Mekong Technology'
    COMPANY_LOGO = 'static/img/mekong_logo.png'
    
    # Position Management Settings
    POSITION_MANAGEMENT = {
        'departments': [
            'engineering',
            'product', 
            'design',
            'marketing',
            'sales',
            'operations'
        ],
        'levels': [
            'junior',      # 0-2 years
            'mid',         # 3-5 years  
            'senior',      # 5-8 years
            'lead'         # 8+ years
        ],
        'default_salary_ranges': {
            'junior': {'min': 8000000, 'max': 12000000},
            'mid': {'min': 12000000, 'max': 18000000},
            'senior': {'min': 18000000, 'max': 25000000},
            'lead': {'min': 25000000, 'max': 35000000}
        }
    }
    
    # Question Management Settings
    QUESTION_MANAGEMENT = {
        'step1_questions_per_assessment': {
            'iq': 10,
            'technical': 15
        },
        'step2_questions_per_interview': 8,
        'step3_questions_per_interview': {
            'cto': 9,
            'ceo': 6
        },
        'auto_scoring': {
            'step1_only': True,
            'pass_threshold': 70,
            'manual_review_range': [50, 69]
        },
        'manual_evaluation': {
            'step2_min_score': 6,  # Out of 10
            'step3_cto_weight': 0.6,
            'step3_ceo_weight': 0.4
        }
    }
    
    # Salary Ranges (VND/month)
    SALARY_RANGES = {
        'Lead Software Developer': {'min': 10000000, 'max': 15000000},
        'Software Engineer': {'min': 8000000, 'max': 12000000},
        'DevOps Engineer': {'min': 9000000, 'max': 13000000},
        'QA Engineer': {'min': 7000000, 'max': 10000000}
    }
    
    # Question Bank Management
    QUESTION_MANAGEMENT = {
        'bulk_import_formats': ['json', 'excel', 'csv'],
        'max_questions_per_import': 1000,
        'question_validation_required': True,
        'backup_before_update': True,
        'version_control': True
    }
    
    # Security Settings
    LINK_SECURITY = {
        'token_length': 32,
        'one_time_use': True,
        'ip_restriction': False,     # Set True for production
        'browser_fingerprint': False # Set True for enhanced security
    }
    
    # Redis Configuration for Rate Limiting
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    
    # Rate Limiting Configuration
    RATE_LIMITS = {
        'login': {'requests': 5, 'window': 300},      # 5 attempts per 5 minutes
        'assessment': {'requests': 100, 'window': 3600},  # 100 requests per hour
        'api': {'requests': 1000, 'window': 3600},    # 1000 requests per hour
        'upload': {'requests': 10, 'window': 3600},   # 10 uploads per hour
        'export': {'requests': 20, 'window': 3600},   # 20 exports per hour
        'interview': {'requests': 50, 'window': 3600}, # 50 interview actions per hour
        'executive': {'requests': 30, 'window': 3600} # 30 executive actions per hour
    }
    
    # Audit Logging Configuration
    AUDIT_LOGGING = {
        'enabled': True,
        'log_level': 'INFO',
        'sensitive_actions': [
            'user_login', 'user_logout', 'password_change', 'password_reset',
            'candidate_create', 'candidate_update', 'candidate_delete',
            'assessment_start', 'assessment_submit', 'assessment_score',
            'interview_schedule', 'interview_evaluate', 'interview_decision',
            'executive_decision', 'compensation_approval', 'file_upload',
            'data_export', 'admin_action', 'permission_change'
        ],
        'retention_days': 365,  # Keep audit logs for 1 year
        'export_enabled': True  # Allow export of audit logs
    }
    
    # Temporary Credentials Settings
    CANDIDATE_CREDENTIALS = {
        'username_format': '{first_name}_{phone_last4}',  # e.g., john_1234
        'password_length': 8,
        'password_complexity': {
            'include_uppercase': True,
            'include_lowercase': True,
            'include_numbers': True,
            'include_special': False,  # Keep simple for candidates
            'exclude_ambiguous': True  # Exclude 0, O, 1, l, I
        },
        'expiration_same_as_link': True,
        'force_password_change': False,  # Keep original for simplicity
        'max_login_attempts': 3,
        'session_timeout_minutes': 60,
        'auto_logout_inactive_minutes': 30
    }
    
    # Approval Workflow Settings
    APPROVAL_WORKFLOW = {
        'step1_auto_approve_threshold': 70,  # Auto-approve if score >= 70%
        'step1_manual_review_range': [50, 69],  # HR can manually review this range
        'step1_auto_reject_threshold': 49,  # Auto-reject if score < 50%
        'step2_interviewer_approval_required': True,
        'step2_min_score_to_pass': 6,  # Out of 10 scale
        'step3_require_both_cto_ceo': True,
        'step3_cto_weight': 0.6,  # Technical assessment weight
        'step3_ceo_weight': 0.4,  # Cultural/business fit weight
        'admin_can_override_any': True
    }
    
    # Email Templates
    EMAIL_TEMPLATES = {
        'step1_invitation': {
            'subject': 'Mekong Technology - Online Assessment Invitation',
            'template': 'step1_invitation.html'
        },
        'step1_credentials': {
            'subject': 'Your Assessment Credentials - Mekong Technology',
            'template': 'step1_credentials.html'
        },
        'step1_reminder': {
            'subject': 'Reminder: Complete your assessment - {hours}h remaining',
            'template': 'step1_reminder.html'
        },
        'step1_expired': {
            'subject': 'Assessment Link Expired - New Link Available',
            'template': 'step1_expired.html'
        },
        'step1_approved': {
            'subject': 'Assessment Passed - Next Step Information',
            'template': 'step1_approved.html'
        },
        'step1_manual_review': {
            'subject': 'Assessment Under Review',
            'template': 'step1_manual_review.html'
        },
        'step2_invitation': {
            'subject': 'Mekong Technology - Technical Interview Invitation',
            'template': 'step2_invitation.html'
        },
        'step2_approved': {
            'subject': 'Technical Interview Passed - Final Interview',
            'template': 'step2_approved.html'
        },
        'step3_notification': {
            'subject': 'Mekong Technology - Final Interview Invitation',
            'template': 'step3_notification.html'
        },
        'final_decision': {
            'subject': 'Recruitment Decision - Mekong Technology',
            'template': 'final_decision.html'
        }
    }

class DevelopmentConfig(Config):
    """
    Development environment configuration.
    
    Provides development-specific settings with debugging enabled
    and SQLite database for local development.
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///recruitment_dev.db'
    SQLALCHEMY_ECHO = True  # Log SQL queries
    
    # Development-specific settings
    TESTING = False
    WTF_CSRF_ENABLED = True
    
    # Development security settings (less strict)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # Longer sessions for development

class ProductionConfig(Config):
    """
    Production environment configuration.
    
    Provides production-specific settings with security hardening,
    PostgreSQL database, and performance optimizations.
    """
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///recruitment_prod.db'
    
    # Security settings for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)
    
    # Production-specific settings
    TESTING = False
    WTF_CSRF_ENABLED = True
    
    # Enhanced security for production
    LINK_SECURITY = {
        'token_length': 64,
        'one_time_use': True,
        'ip_restriction': True,
        'browser_fingerprint': True
    }
    
    # Production email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

class TestingConfig(Config):
    """
    Testing environment configuration.
    
    Provides testing-specific settings with in-memory database
    and disabled CSRF for automated testing.
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///recruitment_test.db'
    WTF_CSRF_ENABLED = False
    
    # Testing-specific settings
    DEBUG = False
    
    # Disable email sending during tests
    MAIL_SERVER = None
    MAIL_USERNAME = None
    MAIL_PASSWORD = None

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: str = None) -> Config:
    """
    Get configuration object based on environment.
    
    Args:
        config_name (str): Configuration name (development, production, testing)
        
    Returns:
        Config: Configuration object for the specified environment
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default']) 