"""
Utility Functions for Mekong Recruitment System

This module provides utility functions following AGENT_RULES_DEVELOPER:
- Temporary credential generation
- Security utilities
- Audit logging
- IP address tracking
- Password generation algorithms
"""

import secrets
import string
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import request, current_app
from werkzeug.security import generate_password_hash

from . import db
from .models import AuditLog, CandidateCredentials, User

logger = logging.getLogger(__name__)

def generate_secure_password(length: int = 8, **kwargs) -> str:
    """
    Generate secure password for candidate credentials.
    
    Args:
        length (int): Password length
        **kwargs: Additional complexity options
        
    Returns:
        str: Generated password
    """
    # Get complexity settings from config
    complexity = current_app.config.get('CANDIDATE_CREDENTIALS', {}).get('password_complexity', {})
    
    # Character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"
    
    # Build character pool based on complexity settings
    chars = ""
    if complexity.get('include_lowercase', True):
        chars += lowercase
    if complexity.get('include_uppercase', True):
        chars += uppercase
    if complexity.get('include_numbers', True):
        chars += digits
    if complexity.get('include_special', False):
        chars += special
    
    # Remove ambiguous characters if specified
    if complexity.get('exclude_ambiguous', True):
        ambiguous = "0O1lI"
        chars = ''.join(c for c in chars if c not in ambiguous)
    
    # Ensure at least one character from each required set
    password = ""
    if complexity.get('include_lowercase', True):
        password += secrets.choice(lowercase)
    if complexity.get('include_uppercase', True):
        password += secrets.choice(uppercase)
    if complexity.get('include_numbers', True):
        password += secrets.choice(digits)
    if complexity.get('include_special', False):
        password += secrets.choice(special)
    
    # Fill remaining length
    remaining_length = length - len(password)
    password += ''.join(secrets.choice(chars) for _ in range(remaining_length))
    
    # Shuffle the password
    password_list = list(password)
    secrets.SystemRandom().shuffle(password_list)
    return ''.join(password_list)

def generate_candidate_username(first_name: str, phone: str) -> str:
    """
    Generate username for candidate based on config format.
    
    Args:
        first_name (str): Candidate's first name
        phone (str): Candidate's phone number
        
    Returns:
        str: Generated username
    """
    username_format = current_app.config.get('CANDIDATE_CREDENTIALS', {}).get('username_format', '{first_name}_{phone_last4}')
    
    # Clean first name (lowercase, no spaces)
    clean_first_name = first_name.lower().replace(' ', '')
    
    # Get last 4 digits of phone
    phone_last4 = phone[-4:] if len(phone) >= 4 else phone
    
    # Generate username
    username = username_format.format(
        first_name=clean_first_name,
        phone_last4=phone_last4
    )
    
    return username

def create_candidate_credentials(candidate_id: int, first_name: str, phone: str) -> Dict[str, Any]:
    """
    Create temporary credentials for candidate.
    
    Args:
        candidate_id (int): Candidate ID
        first_name (str): Candidate's first name
        phone (str): Candidate's phone number
        
    Returns:
        Dict[str, Any]: Credentials information
    """
    # Generate username and password
    username = generate_candidate_username(first_name, phone)
    password = generate_secure_password()
    
    # Set expiration (same as assessment link)
    expiration_days = current_app.config.get('LINK_EXPIRATION_DAYS', {}).get('step1_default', 7)
    expires_at = datetime.utcnow() + timedelta(days=expiration_days)
    
    # Create credentials record
    credentials = CandidateCredentials(
        candidate_id=candidate_id,
        username=username,
        password=password,
        expires_at=expires_at,
        is_active=True
    )
    
    try:
        db.session.add(credentials)
        db.session.commit()
        
        # Log credential creation
        log_audit_event(
            user_id=None,  # System action
            action='create_candidate_credentials',
            resource_type='candidate_credentials',
            resource_id=credentials.id,
            details={
                'candidate_id': candidate_id,
                'username': username,
                'expires_at': expires_at.isoformat()
            }
        )
        
        return {
            'username': username,
            'password': password,
            'expires_at': expires_at,
            'credentials_id': credentials.id
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating candidate credentials: {e}")
        raise

def validate_candidate_credentials(username: str, password: str) -> Optional[CandidateCredentials]:
    """
    Validate candidate credentials.
    
    Args:
        username (str): Username
        password (str): Password
        
    Returns:
        Optional[CandidateCredentials]: Valid credentials or None
    """
    credentials = CandidateCredentials.query.filter_by(username=username).first()
    
    if not credentials:
        return None
    
    # Check if credentials are active
    if not credentials.is_active:
        return None
    
    # Check if credentials have expired
    if credentials.is_expired():
        return None
    
    # Check if account is locked
    if credentials.is_locked():
        return None
    
    # Verify password
    if not credentials.check_password(password):
        credentials.increment_login_attempts()
        db.session.commit()
        return None
    
    # Reset login attempts on successful login
    credentials.reset_login_attempts()
    credentials.ip_address = get_client_ip()
    db.session.commit()
    
    return credentials

def get_client_ip() -> str:
    """
    Get client IP address with proxy support.
    
    Returns:
        str: Client IP address
    """
    # Check for proxy headers
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def log_audit_event(user_id: Optional[int], action: str, resource_type: str, 
                   resource_id: Optional[int], details: Dict[str, Any]) -> None:
    """
    Log audit event for security tracking.
    
    Args:
        user_id (Optional[int]): User ID performing action
        action (str): Action being performed
        resource_type (str): Type of resource
        resource_id (Optional[int]): Resource ID
        details (Dict[str, Any]): Additional details
    """
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details),
            ip_address=get_client_ip(),
            user_agent=request.user_agent.string if request.user_agent else None,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Error logging audit event: {e}")
        db.session.rollback()

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for secure file uploads.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    import re
    import os
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove special characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:100-len(ext)] + ext
    
    return filename

def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """
    Validate file extension for uploads.
    
    Args:
        filename (str): Filename to validate
        allowed_extensions (set): Set of allowed extensions
        
    Returns:
        bool: True if extension is allowed
    """
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions

def calculate_assessment_score(answers: Dict[str, Any], questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate assessment score for Step 1.
    
    Args:
        answers (Dict[str, Any]): User answers
        questions (List[Dict[str, Any]]): Question bank
        
    Returns:
        Dict[str, Any]: Score breakdown
    """
    total_score = 0
    max_score = 0
    iq_score = 0
    technical_score = 0
    iq_questions = 0
    technical_questions = 0
    
    for question in questions:
        question_id = str(question['id'])
        if question_id in answers:
            if answers[question_id] == question['correct_answer']:
                points = question.get('points', 1)
                total_score += points
                
                if question['question_type'] == 'iq':
                    iq_score += points
                    iq_questions += 1
                else:
                    technical_score += points
                    technical_questions += 1
        
        max_score += question.get('points', 1)
    
    # Calculate percentages
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    iq_percentage = (iq_score / (iq_questions * 2) * 100) if iq_questions > 0 else 0
    technical_percentage = (technical_score / (technical_questions * 2) * 100) if technical_questions > 0 else 0
    
    return {
        'total_score': total_score,
        'max_score': max_score,
        'percentage': round(percentage, 2),
        'iq_score': iq_score,
        'technical_score': technical_score,
        'iq_percentage': round(iq_percentage, 2),
        'technical_percentage': round(technical_percentage, 2),
        'passed': percentage >= 70,
        'requires_manual_review': 50 <= percentage <= 69
    }

def format_currency(amount: int, currency: str = 'VND') -> str:
    """
    Format currency for display.
    
    Args:
        amount (int): Amount in VND
        currency (str): Currency code
        
    Returns:
        str: Formatted currency string
    """
    if currency == 'VND':
        return f"{amount:,} VNĐ"
    else:
        return f"{amount:,} {currency}"

def get_position_salary_range(position_level: str) -> Dict[str, int]:
    """
    Get salary range for position level.
    
    Args:
        position_level (str): Position level (junior, mid, senior, lead)
        
    Returns:
        Dict[str, int]: Salary range
    """
    salary_ranges = current_app.config.get('POSITION_MANAGEMENT', {}).get('default_salary_ranges', {})
    return salary_ranges.get(position_level, {'min': 0, 'max': 0})

def is_weekend(date: datetime) -> bool:
    """
    Check if date is weekend.
    
    Args:
        date (datetime): Date to check
        
    Returns:
        bool: True if weekend
    """
    return date.weekday() >= 5

def should_auto_extend_link(expires_at: datetime) -> bool:
    """
    Check if link should be auto-extended (weekend expiry).
    
    Args:
        expires_at (datetime): Expiration date
        
    Returns:
        bool: True if should auto-extend
    """
    config = current_app.config.get('REMINDER_SCHEDULE', {})
    if not config.get('weekend_auto_extend', False):
        return False
    
    return is_weekend(expires_at)

def generate_assessment_token() -> str:
    """
    Generate secure token for assessment links.
    
    Returns:
        str: Generated token
    """
    token_length = current_app.config.get('LINK_SECURITY', {}).get('token_length', 32)
    return secrets.token_urlsafe(token_length)

def validate_assessment_token(token: str) -> bool:
    """
    Validate assessment token.
    
    Args:
        token (str): Token to validate
        
    Returns:
        bool: True if valid
    """
    # Basic validation - in production, tokens would be stored in database
    if not token or len(token) < 20:
        return False
    
    return True

def get_candidate_progress(candidate_id: int) -> Dict[str, Any]:
    """
    Get candidate progress through recruitment process.
    
    Args:
        candidate_id (int): Candidate ID
        
    Returns:
        Dict[str, Any]: Progress information
    """
    from .models import Candidate, AssessmentResult, InterviewEvaluation
    
    candidate = Candidate.query.get(candidate_id)
    if not candidate:
        return {}
    
    # Get assessment results
    step1_result = AssessmentResult.query.filter_by(
        candidate_id=candidate_id, 
        step='step1'
    ).first()
    
    step2_evaluations = InterviewEvaluation.query.filter_by(
        candidate_id=candidate_id,
        step='step2'
    ).all()
    
    step3_evaluations = InterviewEvaluation.query.filter_by(
        candidate_id=candidate_id,
        step='step3'
    ).all()
    
    return {
        'candidate_id': candidate_id,
        'status': candidate.status,
        'current_step': candidate.get_current_step(),
        'step1_completed': step1_result is not None,
        'step1_score': step1_result.percentage if step1_result else None,
        'step1_passed': step1_result.is_passed() if step1_result else False,
        'step2_completed': len(step2_evaluations) > 0,
        'step2_approved': any(eval.recommendation == 'approve' for eval in step2_evaluations),
        'step3_completed': len(step3_evaluations) > 0,
        'step3_approved': all(eval.recommendation == 'approve' for eval in step3_evaluations),
        'created_at': candidate.created_at,
        'updated_at': candidate.updated_at
    } 

def log_activity(user_id: Optional[int], action: str, details: Dict[str, Any] = None) -> None:
    """
    Log user activity for tracking and analytics.
    
    Args:
        user_id (Optional[int]): User ID performing action
        action (str): Action being performed
        details (Dict[str, Any]): Additional details
    """
    try:
        # Use existing audit logging function
        log_audit_event(
            user_id=user_id,
            action=action,
            resource_type='activity',
            resource_id=None,
            details=details or {}
        )
        
        # Additional activity-specific logging if needed
        logger.info(f"Activity logged: {action} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error logging activity: {e}")

def send_email(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """
    Send email notification (placeholder implementation).
    
    Args:
        to_email (str): Recipient email
        subject (str): Email subject
        body (str): Plain text body
        html_body (str): HTML body (optional)
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        # Get email configuration
        email_config = current_app.config.get('EMAIL_CONFIG', {})
        
        # Log email attempt
        logger.info(f"Email sent to {to_email}: {subject}")
        
        # In production, this would use SMTP or email service
        # For now, just log the email details
        email_details = {
            'to': to_email,
            'subject': subject,
            'body': body,
            'html_body': html_body,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Log email details for debugging
        logger.info(f"Email details: {email_details}")
        
        # In a real implementation, you would:
        # 1. Configure SMTP settings
        # 2. Create email message
        # 3. Send via SMTP
        # 4. Handle errors and retries
        
        # For development/testing, return success
        return True
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False

def send_assessment_reminder(candidate_email: str, candidate_name: str, 
                           assessment_link: str, expires_at: datetime) -> bool:
    """
    Send assessment reminder email to candidate.
    
    Args:
        candidate_email (str): Candidate email
        candidate_name (str): Candidate name
        assessment_link (str): Assessment link
        expires_at (datetime): Expiration date
        
    Returns:
        bool: True if email sent successfully
    """
    subject = "Nhắc nhở: Hoàn thành bài đánh giá tuyển dụng"
    
    body = f"""
    Xin chào {candidate_name},
    
    Đây là nhắc nhở về bài đánh giá tuyển dụng của bạn.
    
    Link đánh giá: {assessment_link}
    Hạn hoàn thành: {expires_at.strftime('%d/%m/%Y %H:%M')}
    
    Vui lòng hoàn thành bài đánh giá trước khi hết hạn.
    
    Trân trọng,
    Đội ngũ Tuyển dụng Mekong Technology
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>Nhắc nhở: Hoàn thành bài đánh giá tuyển dụng</h2>
        <p>Xin chào <strong>{candidate_name}</strong>,</p>
        <p>Đây là nhắc nhở về bài đánh giá tuyển dụng của bạn.</p>
        <p><strong>Link đánh giá:</strong> <a href="{assessment_link}">{assessment_link}</a></p>
        <p><strong>Hạn hoàn thành:</strong> {expires_at.strftime('%d/%m/%Y %H:%M')}</p>
        <p>Vui lòng hoàn thành bài đánh giá trước khi hết hạn.</p>
        <br>
        <p>Trân trọng,<br>
        Đội ngũ Tuyển dụng Mekong Technology</p>
    </body>
    </html>
    """
    
    return send_email(candidate_email, subject, body, html_body)

def send_interview_invitation(candidate_email: str, candidate_name: str,
                            interview_link: str, interview_date: datetime,
                            interviewer_name: str) -> bool:
    """
    Send interview invitation email to candidate.
    
    Args:
        candidate_email (str): Candidate email
        candidate_name (str): Candidate name
        interview_link (str): Interview link
        interview_date (datetime): Interview date
        interviewer_name (str): Interviewer name
        
    Returns:
        bool: True if email sent successfully
    """
    subject = "Thư mời phỏng vấn - Mekong Technology"
    
    body = f"""
    Xin chào {candidate_name},
    
    Chúng tôi rất vui mừng thông báo rằng bạn đã vượt qua vòng đánh giá đầu tiên.
    
    Bạn được mời tham gia phỏng vấn kỹ thuật với:
    - Người phỏng vấn: {interviewer_name}
    - Thời gian: {interview_date.strftime('%d/%m/%Y %H:%M')}
    - Link phỏng vấn: {interview_link}
    
    Vui lòng chuẩn bị và tham gia đúng giờ.
    
    Trân trọng,
    Đội ngũ Tuyển dụng Mekong Technology
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>Thư mời phỏng vấn - Mekong Technology</h2>
        <p>Xin chào <strong>{candidate_name}</strong>,</p>
        <p>Chúng tôi rất vui mừng thông báo rằng bạn đã vượt qua vòng đánh giá đầu tiên.</p>
        <p>Bạn được mời tham gia phỏng vấn kỹ thuật với:</p>
        <ul>
            <li><strong>Người phỏng vấn:</strong> {interviewer_name}</li>
            <li><strong>Thời gian:</strong> {interview_date.strftime('%d/%m/%Y %H:%M')}</li>
            <li><strong>Link phỏng vấn:</strong> <a href="{interview_link}">{interview_link}</a></li>
        </ul>
        <p>Vui lòng chuẩn bị và tham gia đúng giờ.</p>
        <br>
        <p>Trân trọng,<br>
        Đội ngũ Tuyển dụng Mekong Technology</p>
    </body>
    </html>
    """
    
    return send_email(candidate_email, subject, body, html_body) 