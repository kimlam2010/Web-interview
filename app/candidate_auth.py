"""
Candidate Authentication Module for Mekong Recruitment System

This module provides secure temporary authentication for candidates following AGENT_RULES_DEVELOPER:
- Auto-generation username/password
- Credential expiration logic
- Secure password generation algorithm
- Login attempt tracking cho candidates
- Session timeout cho candidate accounts
- IP address tracking
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging
import secrets
import string
from typing import Optional, Tuple

from . import db
from .models import CandidateCredentials, Candidate, AuditLog
from app.utils import log_audit_event, get_client_ip

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
candidate_auth_bp = Blueprint('candidate_auth', __name__)

# Forms
class CandidateLoginForm(FlaskForm):
    """Candidate login form with validation."""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Start Assessment')

def generate_secure_password(length: int = 12) -> str:
    """
    Generate a secure random password.
    
    Args:
        length (int): Password length
        
    Returns:
        str: Secure password
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure password has at least one of each type
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password

def generate_candidate_username(candidate: Candidate) -> str:
    """
    Generate unique username for candidate.
    
    Args:
        candidate (Candidate): Candidate object
        
    Returns:
        str: Unique username
    """
    base_username = f"{candidate.first_name.lower()}{candidate.last_name.lower()}{candidate.id}"
    return base_username

def create_candidate_credentials(candidate: Candidate, expiry_days: int = 7) -> Tuple[str, str]:
    """
    Create temporary credentials for candidate.
    
    Args:
        candidate (Candidate): Candidate object
        expiry_days (int): Days until credentials expire
        
    Returns:
        Tuple[str, str]: (username, plain_password)
    """
    # Generate username
    username = generate_candidate_username(candidate)
    
    # Generate secure password
    password = generate_secure_password()
    
    # Set expiration
    expires_at = datetime.utcnow() + timedelta(days=expiry_days)
    
    # Create credentials
    credentials = CandidateCredentials(
        candidate_id=candidate.id,
        username=username,
        expires_at=expires_at,
        ip_address=get_client_ip()
    )
    credentials.set_password(password)
    
    # Save to database
    db.session.add(credentials)
    db.session.commit()
    
    # Log creation
    log_audit_event(
        user_id=None,
        action='candidate_credentials_created',
        resource_type='candidate_credentials',
        resource_id=credentials.id,
        details={
            'candidate_id': candidate.id,
            'username': username,
            'expires_at': expires_at.isoformat(),
            'ip_address': get_client_ip()
        }
    )
    
    return username, password

def extend_candidate_credentials(candidate_id: int, additional_days: int = 3) -> bool:
    """
    Extend candidate credentials expiration.
    
    Args:
        candidate_id (int): Candidate ID
        additional_days (int): Additional days to extend
        
    Returns:
        bool: True if extended successfully
    """
    credentials = CandidateCredentials.query.filter_by(
        candidate_id=candidate_id,
        is_active=True
    ).first()
    
    if not credentials or credentials.is_expired():
        return False
    
    # Extend expiration
    credentials.expires_at += timedelta(days=additional_days)
    db.session.commit()
    
    # Log extension
    log_audit_event(
        user_id=None,
        action='candidate_credentials_extended',
        resource_type='candidate_credentials',
        resource_id=credentials.id,
        details={
            'candidate_id': candidate_id,
            'new_expires_at': credentials.expires_at.isoformat(),
            'additional_days': additional_days
        }
    )
    
    return True

@candidate_auth_bp.route('/candidate/login', methods=['GET', 'POST'])
def candidate_login():
    """
    Candidate login endpoint with security features.
    
    Features:
    - Credential validation
    - Expiration checking
    - Login attempt tracking
    - IP address tracking
    - Audit logging
    """
    form = CandidateLoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        # Find credentials
        credentials = CandidateCredentials.query.filter_by(
            username=username,
            is_active=True
        ).first()
        
        if not credentials:
            flash('Invalid credentials or assessment link expired.', 'error')
            log_failed_candidate_login(username, 'invalid_credentials')
            return render_template('candidate/login.html', form=form)
        
        # Check expiration
        if credentials.is_expired():
            flash('Assessment link has expired. Please contact HR for a new link.', 'error')
            log_failed_candidate_login(username, 'expired_credentials')
            return render_template('candidate/login.html', form=form)
        
        # Check if locked
        if credentials.is_locked():
            flash('Account temporarily locked due to too many failed attempts. Please try again later.', 'error')
            return render_template('candidate/login.html', form=form)
        
        # Verify password
        if not credentials.check_password(password):
            credentials.increment_login_attempts()
            db.session.commit()
            
            flash('Invalid credentials. Please try again.', 'error')
            log_failed_candidate_login(username, 'invalid_password')
            return render_template('candidate/login.html', form=form)
        
        # Successful login
        credentials.reset_login_attempts()
        credentials.last_login = datetime.utcnow()
        credentials.ip_address = get_client_ip()
        db.session.commit()
        
        # Log successful login
        log_audit_event(
            user_id=None,
            action='candidate_login_success',
            resource_type='candidate_credentials',
            resource_id=credentials.id,
            details={
                'candidate_id': credentials.candidate_id,
                'username': username,
                'ip_address': get_client_ip()
            }
        )
        
        # Set session
        session['candidate_id'] = credentials.candidate_id
        session['candidate_username'] = username
        session['candidate_login_time'] = datetime.utcnow().isoformat()
        
        flash('Welcome! You can now start your assessment.', 'success')
        return redirect(url_for('assessment.start_assessment'))
    
    return render_template('candidate/login.html', form=form)

@candidate_auth_bp.route('/candidate/logout')
def candidate_logout():
    """
    Candidate logout endpoint.
    """
    candidate_id = session.get('candidate_id')
    username = session.get('candidate_username')
    
    if candidate_id:
        # Log logout
        log_audit_event(
            user_id=None,
            action='candidate_logout',
            resource_type='candidate_credentials',
            resource_id=candidate_id,
            details={
                'candidate_id': candidate_id,
                'username': username,
                'ip_address': get_client_ip()
            }
        )
    
    # Clear session
    session.pop('candidate_id', None)
    session.pop('candidate_username', None)
    session.pop('candidate_login_time', None)
    
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('candidate_auth.candidate_login'))

@candidate_auth_bp.route('/candidate/extend-link', methods=['POST'])
def extend_assessment_link():
    """
    Extend assessment link expiration.
    """
    candidate_id = session.get('candidate_id')
    
    if not candidate_id:
        flash('Please log in first.', 'error')
        return redirect(url_for('candidate_auth.candidate_login'))
    
    if extend_candidate_credentials(candidate_id):
        flash('Assessment link extended successfully.', 'success')
    else:
        flash('Unable to extend assessment link. Please contact HR.', 'error')
    
    return redirect(url_for('assessment.start_assessment'))

def log_failed_candidate_login(username: str, reason: str) -> None:
    """
    Log failed candidate login attempt.
    
    Args:
        username (str): Username attempted
        reason (str): Reason for failure
    """
    log_audit_event(
        user_id=None,
        action='candidate_login_failed',
        resource_type='candidate_credentials',
        resource_id=None,
        details={
            'username': username,
            'reason': reason,
            'ip_address': get_client_ip()
        }
    )

@candidate_auth_bp.before_request
def before_candidate_request():
    """
    Before request handler for candidate authentication.
    """
    # Check session timeout for candidates (4 hours)
    login_time = session.get('candidate_login_time')
    if login_time:
        login_datetime = datetime.fromisoformat(login_time)
        if datetime.utcnow() - login_datetime > timedelta(hours=4):
            # Session expired
            session.clear()
            flash('Session expired. Please log in again.', 'warning')
            return redirect(url_for('candidate_auth.candidate_login'))

def cleanup_expired_credentials() -> int:
    """
    Clean up expired candidate credentials.
    
    Returns:
        int: Number of credentials cleaned up
    """
    expired_credentials = CandidateCredentials.query.filter(
        CandidateCredentials.expires_at < datetime.utcnow(),
        CandidateCredentials.is_active == True
    ).all()
    
    count = 0
    for credential in expired_credentials:
        credential.is_active = False
        count += 1
    
    if count > 0:
        db.session.commit()
        logger.info(f"Cleaned up {count} expired candidate credentials")
    
    return count

def get_candidate_session_info() -> Optional[dict]:
    """
    Get current candidate session information.
    
    Returns:
        Optional[dict]: Session info or None if not logged in
    """
    candidate_id = session.get('candidate_id')
    if not candidate_id:
        return None
    
    return {
        'candidate_id': candidate_id,
        'username': session.get('candidate_username'),
        'login_time': session.get('candidate_login_time')
    } 