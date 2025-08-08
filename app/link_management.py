"""
Link Management System for Mekong Recruitment System

This module provides assessment link management following AGENT_RULES_DEVELOPER:
- Tạo auto-generation assessment links
- Implement link expiration logic (7 days default)
- Tạo link extension functionality
- Implement weekend auto-extension
- Tạo email reminders (24h, 3h before expiry)
- Implement link status tracking
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Optional
from datetime import datetime, timedelta
import secrets
import string
import logging
from typing import Dict, Any, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from . import db
from .models import Candidate, CandidateCredentials, AssessmentLink, AuditLog
from app.utils import log_audit_event, get_client_ip
from .candidate_auth import create_candidate_credentials

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
link_management_bp = Blueprint('link_management', __name__)

# Forms
class AssessmentLinkForm(FlaskForm):
    """Form for creating assessment links."""
    candidate_id = SelectField('Candidate', coerce=int, validators=[DataRequired()])
    expiry_days = IntegerField('Expiry Days', validators=[DataRequired()], default=7)
    custom_message = StringField('Custom Message', validators=[Optional()])
    submit = SubmitField('Generate Link')

class LinkExtensionForm(FlaskForm):
    """Form for extending assessment links."""
    additional_days = IntegerField('Additional Days', validators=[DataRequired()], default=3)
    reason = StringField('Reason for Extension', validators=[Optional()])
    submit = SubmitField('Extend Link')

def generate_unique_link_id() -> str:
    """
    Generate unique link ID.
    
    Returns:
        str: Unique link ID
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(16))

def create_assessment_link(candidate: Candidate, expiry_days: int = 7, 
                         custom_message: str = None, created_by: int = None) -> AssessmentLink:
    """
    Create assessment link for candidate.
    
    Args:
        candidate (Candidate): Candidate object
        expiry_days (int): Days until link expires
        custom_message (str): Custom message for candidate
        created_by (int): User ID who created the link
        
    Returns:
        AssessmentLink: Created assessment link
    """
    # Generate unique link ID
    link_id = generate_unique_link_id()
    
    # Set expiration
    expires_at = datetime.utcnow() + timedelta(days=expiry_days)
    
    # Create assessment link
    assessment_link = AssessmentLink(
        candidate_id=candidate.id,
        link_id=link_id,
        expires_at=expires_at,
        status='active',
        custom_message=custom_message,
        created_by=created_by,
        ip_address=get_client_ip()
    )
    
    db.session.add(assessment_link)
    db.session.commit()
    
    # Log link creation
    log_audit_event(
        user_id=created_by,
        action='assessment_link_created',
        resource_type='assessment_link',
        resource_id=assessment_link.id,
        details={
            'candidate_id': candidate.id,
            'link_id': link_id,
            'expires_at': expires_at.isoformat(),
            'ip_address': get_client_ip()
        }
    )
    
    return assessment_link

def extend_assessment_link(link_id: str, additional_days: int, 
                          reason: str = None, extended_by: int = None) -> bool:
    """
    Extend assessment link expiration.
    
    Args:
        link_id (str): Link ID to extend
        additional_days (int): Additional days to extend
        reason (str): Reason for extension
        extended_by (int): User ID who extended the link
        
    Returns:
        bool: True if extended successfully
    """
    link = AssessmentLink.query.filter_by(link_id=link_id, status='active').first()
    
    if not link or link.is_expired():
        return False
    
    # Extend expiration
    link.expires_at += timedelta(days=additional_days)
    link.extension_count += 1
    link.last_extended_by = extended_by
    link.last_extended_at = datetime.utcnow()
    link.extension_reason = reason
    
    db.session.commit()
    
    # Log extension
    log_audit_event(
        user_id=extended_by,
        action='assessment_link_extended',
        resource_type='assessment_link',
        resource_id=link.id,
        details={
            'link_id': link_id,
            'additional_days': additional_days,
            'new_expires_at': link.expires_at.isoformat(),
            'reason': reason,
            'ip_address': get_client_ip()
        }
    )
    
    return True

def get_assessment_link_url(link_id: str) -> str:
    """
    Get assessment link URL.
    
    Args:
        link_id (str): Link ID
        
    Returns:
        str: Assessment link URL
    """
    return f"/candidate/assessment/{link_id}"

def check_weekend_auto_extension() -> int:
    """
    Check and auto-extend links that expire on weekends.
    
    Returns:
        int: Number of links auto-extended
    """
    # Find links expiring on weekends (Friday, Saturday, Sunday)
    weekend_expiry_links = AssessmentLink.query.filter(
        AssessmentLink.status == 'active',
        AssessmentLink.expires_at >= datetime.utcnow(),
        AssessmentLink.expires_at <= datetime.utcnow() + timedelta(days=3),
        db.func.extract('dow', AssessmentLink.expires_at).in_([5, 6, 0])  # Friday=5, Saturday=6, Sunday=0
    ).all()
    
    extended_count = 0
    for link in weekend_expiry_links:
        # Auto-extend by 2 days to move to Monday
        link.expires_at += timedelta(days=2)
        link.auto_extended = True
        link.auto_extension_date = datetime.utcnow()
        extended_count += 1
    
    if extended_count > 0:
        db.session.commit()
        logger.info(f"Auto-extended {extended_count} weekend-expiring assessment links")
    
    return extended_count

def send_expiry_reminder(link: AssessmentLink, hours_before: int) -> bool:
    """
    Send expiry reminder email.
    
    Args:
        link (AssessmentLink): Assessment link
        hours_before (int): Hours before expiry to send reminder
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        candidate = link.candidate
        
        # Check if reminder already sent
        reminder_key = f"reminder_{hours_before}h_sent"
        if getattr(link, reminder_key, False):
            return True
        
        # Calculate time until expiry
        time_until_expiry = link.expires_at - datetime.utcnow()
        hours_remaining = time_until_expiry.total_seconds() / 3600
        
        if hours_remaining <= hours_before:
            # Send email reminder
            subject = f"Assessment Link Expires Soon - {candidate.first_name} {candidate.last_name}"
            
            if hours_before == 24:
                message = f"""
                Dear {candidate.first_name} {candidate.last_name},
                
                Your assessment link will expire in approximately 24 hours.
                Please complete your assessment before the link expires.
                
                Assessment Link: {get_assessment_link_url(link.link_id)}
                Expires: {link.expires_at.strftime('%B %d, %Y at %I:%M %p')}
                
                If you need more time, please contact HR immediately.
                
                Best regards,
                Mekong Technology HR Team
                """
            else:  # 3 hours
                message = f"""
                Dear {candidate.first_name} {candidate.last_name},
                
                URGENT: Your assessment link will expire in approximately 3 hours.
                Please complete your assessment immediately.
                
                Assessment Link: {get_assessment_link_url(link.link_id)}
                Expires: {link.expires_at.strftime('%B %d, %Y at %I:%M %p')}
                
                If you cannot complete the assessment, please contact HR immediately.
                
                Best regards,
                Mekong Technology HR Team
                """
            
            # Send email (implementation depends on email configuration)
            success = send_email(candidate.email, subject, message)
            
            if success:
                # Mark reminder as sent
                setattr(link, reminder_key, True)
                db.session.commit()
                
                # Log reminder sent
                log_audit_event(
                    user_id=None,
                    action='expiry_reminder_sent',
                    resource_type='assessment_link',
                    resource_id=link.id,
                    details={
                        'candidate_id': candidate.id,
                        'hours_before': hours_before,
                        'email': candidate.email
                    }
                )
            
            return success
        
        return False
    
    except Exception as e:
        logger.error(f"Failed to send expiry reminder: {e}")
        return False

def send_email(to_email: str, subject: str, message: str) -> bool:
    """
    Send email (placeholder implementation).
    
    Args:
        to_email (str): Recipient email
        subject (str): Email subject
        message (str): Email message
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        # This is a placeholder implementation
        # In production, use proper email service (SendGrid, AWS SES, etc.)
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def cleanup_expired_links() -> int:
    """
    Clean up expired assessment links.
    
    Returns:
        int: Number of links cleaned up
    """
    expired_links = AssessmentLink.query.filter(
        AssessmentLink.status == 'active',
        AssessmentLink.expires_at < datetime.utcnow()
    ).all()
    
    count = 0
    for link in expired_links:
        link.status = 'expired'
        link.expired_at = datetime.utcnow()
        count += 1
    
    if count > 0:
        db.session.commit()
        logger.info(f"Cleaned up {count} expired assessment links")
    
    return count

@link_management_bp.route('/links')
@login_required
def link_management():
    """
    Assessment link management page.
    """
    # Get active links
    active_links = AssessmentLink.query.filter_by(status='active').order_by(
        AssessmentLink.created_at.desc()
    ).all()
    
    # Get expired links
    expired_links = AssessmentLink.query.filter_by(status='expired').order_by(
        AssessmentLink.expired_at.desc()
    ).limit(10).all()
    
    # Get statistics
    total_links = AssessmentLink.query.count()
    active_count = AssessmentLink.query.filter_by(status='active').count()
    expired_count = AssessmentLink.query.filter_by(status='expired').count()
    used_count = AssessmentLink.query.filter_by(status='used').count()
    
    return render_template('link_management/links.html',
                         active_links=active_links,
                         expired_links=expired_links,
                         total_links=total_links,
                         active_count=active_count,
                         expired_count=expired_count,
                         used_count=used_count)

@link_management_bp.route('/links/create', methods=['GET', 'POST'])
@login_required
def create_link():
    """
    Create new assessment link.
    """
    form = AssessmentLinkForm()
    
    # Get candidates for dropdown
    candidates = Candidate.query.filter_by(status='pending').all()
    form.candidate_id.choices = [(c.id, f"{c.first_name} {c.last_name} - {c.position.title if c.position else 'N/A'}") 
                                for c in candidates]
    
    if form.validate_on_submit():
        candidate = Candidate.query.get(form.candidate_id.data)
        if not candidate:
            flash('Candidate not found.', 'error')
            return redirect(url_for('link_management.create_link'))
        
        # Create assessment link
        assessment_link = create_assessment_link(
            candidate=candidate,
            expiry_days=form.expiry_days.data,
            custom_message=form.custom_message.data,
            created_by=current_user.id
        )
        
        flash(f'Assessment link created successfully. Link ID: {assessment_link.link_id}', 'success')
        return redirect(url_for('link_management.link_management'))
    
    return render_template('link_management/create_link.html', form=form)

@link_management_bp.route('/links/<link_id>/extend', methods=['GET', 'POST'])
@login_required
def extend_link(link_id: str):
    """
    Extend assessment link.
    """
    link = AssessmentLink.query.filter_by(link_id=link_id).first()
    if not link:
        flash('Assessment link not found.', 'error')
        return redirect(url_for('link_management.link_management'))
    
    form = LinkExtensionForm()
    
    if form.validate_on_submit():
        if extend_assessment_link(
            link_id=link_id,
            additional_days=form.additional_days.data,
            reason=form.reason.data,
            extended_by=current_user.id
        ):
            flash('Assessment link extended successfully.', 'success')
        else:
            flash('Failed to extend assessment link.', 'error')
        
        return redirect(url_for('link_management.link_management'))
    
    return render_template('link_management/extend_link.html', form=form, link=link)

@link_management_bp.route('/links/<link_id>/deactivate', methods=['POST'])
@login_required
def deactivate_link(link_id: str):
    """
    Deactivate assessment link.
    """
    link = AssessmentLink.query.filter_by(link_id=link_id).first()
    if not link:
        flash('Assessment link not found.', 'error')
        return redirect(url_for('link_management.link_management'))
    
    link.status = 'deactivated'
    link.deactivated_at = datetime.utcnow()
    link.deactivated_by = current_user.id
    
    db.session.commit()
    
    # Log deactivation
    log_audit_event(
        user_id=current_user.id,
        action='assessment_link_deactivated',
        resource_type='assessment_link',
        resource_id=link.id,
        details={
            'link_id': link_id,
            'ip_address': get_client_ip()
        }
    )
    
    flash('Assessment link deactivated successfully.', 'success')
    return redirect(url_for('link_management.link_management'))

@link_management_bp.route('/api/links/<link_id>/status')
def get_link_status(link_id: str):
    """
    API endpoint to get link status.
    """
    link = AssessmentLink.query.filter_by(link_id=link_id).first()
    
    if not link:
        return jsonify({'error': 'Link not found'}), 404
    
    return jsonify({
        'link_id': link.link_id,
        'status': link.status,
        'expires_at': link.expires_at.isoformat() if link.expires_at else None,
        'is_expired': link.is_expired() if hasattr(link, 'is_expired') else False,
        'created_at': link.created_at.isoformat() if link.created_at else None
    })

@link_management_bp.route('/api/links/cleanup', methods=['POST'])
@login_required
def cleanup_links():
    """
    API endpoint to cleanup expired links.
    """
    count = cleanup_expired_links()
    return jsonify({'cleaned_up': count})

@link_management_bp.route('/api/links/weekend-extension', methods=['POST'])
@login_required
def weekend_auto_extension():
    """
    API endpoint to check and auto-extend weekend expiring links.
    """
    count = check_weekend_auto_extension()
    return jsonify({'auto_extended': count})

@link_management_bp.route('/api/links/send-reminders', methods=['POST'])
@login_required
def send_reminders():
    """
    API endpoint to send expiry reminders.
    """
    # Get links expiring soon
    links_24h = AssessmentLink.query.filter(
        AssessmentLink.status == 'active',
        AssessmentLink.expires_at >= datetime.utcnow(),
        AssessmentLink.expires_at <= datetime.utcnow() + timedelta(hours=24)
    ).all()
    
    links_3h = AssessmentLink.query.filter(
        AssessmentLink.status == 'active',
        AssessmentLink.expires_at >= datetime.utcnow(),
        AssessmentLink.expires_at <= datetime.utcnow() + timedelta(hours=3)
    ).all()
    
    reminders_24h = sum(1 for link in links_24h if send_expiry_reminder(link, 24))
    reminders_3h = sum(1 for link in links_3h if send_expiry_reminder(link, 3))
    
    return jsonify({
        'reminders_24h_sent': reminders_24h,
        'reminders_3h_sent': reminders_3h
    }) 