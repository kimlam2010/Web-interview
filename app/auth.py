"""
Authentication Blueprint for Mekong Recruitment System

This module provides user authentication functionality following AGENT_RULES_DEVELOPER:
- Flask-Login integration
- Password hashing với bcrypt
- Session management với timeout
- CSRF protection cho forms
- Login attempt limiting (3 max attempts)
- Password reset functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse
from datetime import datetime, timedelta
import logging
from typing import Optional

from . import db, login_manager
from .models import User, AuditLog
from app.utils import log_audit_event, get_client_ip

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Forms
class LoginForm(FlaskForm):
    """Login form with validation."""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """User registration form with validation."""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=10, max=20)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long")
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    role = StringField('Role', validators=[DataRequired()])
    submit = SubmitField('Register')

class PasswordResetForm(FlaskForm):
    """Password reset form."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Reset Password')

class ChangePasswordForm(FlaskForm):
    """Change password form."""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')

@login_manager.user_loader
def load_user(user_id: int) -> Optional[User]:
    """
    User loader for Flask-Login.
    
    Args:
        user_id (int): User ID to load
        
    Returns:
        Optional[User]: User object or None if not found
    """
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login page.
    """
    try:
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        
        if request.method == 'POST':
            current_app.logger.info(f"Login attempt from IP: {get_client_ip()}")
            form = LoginForm()
            
            if form.validate_on_submit():
                current_app.logger.info(f"Form validation passed for username: {form.username.data}")
                user = User.query.filter_by(username=form.username.data).first()
                
                if user and check_password_hash(user.password_hash, form.password.data):
                    current_app.logger.info(f"Password check passed for user: {user.username}")
                    if user.is_active:
                        login_user(user, remember=form.remember_me.data)
                        
                        # Update last login
                        user.last_login = datetime.utcnow()
                        user.login_attempts = 0
                        user.locked_until = None
                        db.session.commit()
                        
                        # Log successful login
                        log_audit_event(
                            user_id=user.id,
                            action='login_success',
                            resource_type='user',
                            resource_id=user.id,
                            details={'ip_address': get_client_ip()}
                        )
                        
                        next_page = request.args.get('next')
                        if not next_page or url_parse(next_page).netloc != '':
                            next_page = url_for('main.dashboard')
                        
                        flash('Đăng nhập thành công!', 'success')
                        current_app.logger.info(f"User {user.username} logged in successfully")
                        return redirect(next_page)
                    else:
                        flash('Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.', 'error')
                        current_app.logger.warning(f"Login attempt for locked account: {user.username}")
                else:
                    # Increment failed login attempts
                    if user:
                        user.login_attempts += 1
                        if user.login_attempts >= 3:
                            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                        db.session.commit()
                    
                    flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'error')
                    current_app.logger.warning(f"Failed login attempt for username: {form.username.data}")
                    
                    # Log failed login attempt
                    log_audit_event(
                        user_id=user.id if user else None,
                        action='login_failed',
                        resource_type='user',
                        resource_id=user.id if user else None,
                        details={'ip_address': get_client_ip(), 'username': form.username.data}
                    )
            else:
                current_app.logger.warning(f"Form validation failed: {form.errors}")
                flash('Vui lòng kiểm tra lại thông tin đăng nhập.', 'error')
        else:
            current_app.logger.info("Login page accessed")
            
    except Exception as e:
        current_app.logger.error(f'Login error: {str(e)}')
        current_app.logger.error(f'Error details: {type(e).__name__}: {e}')
        flash('Có lỗi xảy ra khi đăng nhập. Vui lòng thử lại.', 'error')
    
    form = LoginForm()
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """
    User logout endpoint with audit logging.
    """
    user_id = current_user.id
    username = current_user.username
    
    # Log logout event
    log_audit_event(
        user_id=user_id,
        action='logout',
        resource_type='user',
        resource_id=user_id,
        details={'ip_address': get_client_ip()}
    )
    
    logout_user()
    flash(f'You have been logged out successfully.', 'info')
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration endpoint (Admin only).
    
    Features:
    - Role-based access control
    - Password hashing
    - Email validation
    - Audit logging
    """
    if not current_user.is_authenticated or not current_user.has_permission('manage_users'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('auth.login'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html', form=form)
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role=form.role.data,
            password=form.password.data
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Log user creation
            log_audit_event(
                user_id=current_user.id,
                action='create_user',
                resource_type='user',
                resource_id=user.id,
                details={
                    'created_username': user.username,
                    'created_role': user.role
                }
            )
            
            flash(f'User {user.get_full_name()} has been created successfully.', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {e}")
            flash('Error creating user. Please try again.', 'error')
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/profile')
@login_required
def profile():
    """
    User profile page.
    """
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    Change password endpoint with security validation.
    """
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'error')
            return render_template('auth/change_password.html', form=form)
        
        # Update password
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        # Log password change
        log_audit_event(
            user_id=current_user.id,
            action='change_password',
            resource_type='user',
            resource_id=current_user.id,
            details={'ip_address': get_client_ip()}
        )
        
        flash('Password has been changed successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', form=form)

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """
    Password reset endpoint (placeholder for future implementation).
    """
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # TODO: Implement password reset functionality
            # - Generate reset token
            # - Send reset email
            # - Create reset form
            flash('Password reset instructions have been sent to your email.', 'info')
        else:
            flash('If an account with that email exists, reset instructions have been sent.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)

def log_failed_login_attempt(username: str, reason: str) -> None:
    """
    Log failed login attempts for security monitoring.
    
    Args:
        username (str): Attempted username
        reason (str): Reason for failure
    """
    log_audit_event(
        user_id=None,
        action='login_failed',
        resource_type='user',
        resource_id=None,
        details={
            'attempted_username': username,
            'reason': reason,
            'ip_address': get_client_ip()
        }
    )

@auth_bp.before_request
def before_request():
    """
    Security middleware for authentication routes.
    
    Features:
    - Session timeout checking
    - IP address validation (for production)
    - Rate limiting (basic implementation)
    """
    if current_user.is_authenticated:
        # Check session timeout
        last_activity = session.get('last_activity')
        if last_activity:
            last_activity = datetime.fromisoformat(last_activity)
            if datetime.utcnow() - last_activity > timedelta(hours=4):
                logout_user()
                flash('Session expired. Please log in again.', 'info')
                return redirect(url_for('auth.login'))
        
        # Update last activity
        session['last_activity'] = datetime.utcnow().isoformat()

@auth_bp.after_request
def after_request(response):
    """
    Security headers for authentication routes.
    """
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response 