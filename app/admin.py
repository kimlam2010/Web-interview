"""
Admin Blueprint for Mekong Recruitment System

This module provides admin functionality following AGENT_RULES_DEVELOPER:
- User management
- System configuration
- Question bank management
- System analytics
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from .decorators import admin_required, audit_action

# Create blueprint
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@login_required
@admin_required
@audit_action('view_admin_dashboard')
def admin_dashboard():
    """
    Admin dashboard.
    """
    return render_template('admin/dashboard.html')

@admin_bp.route('/users')
@login_required
@admin_required
@audit_action('view_users_management')
def users():
    """
    User management page.
    """
    return render_template('admin/users.html')

@admin_bp.route('/questions')
@login_required
@admin_required
@audit_action('view_questions_management')
def questions():
    """
    Question bank management page.
    """
    return render_template('admin/questions.html')

@admin_bp.route('/system')
@login_required
@admin_required
@audit_action('view_system_config')
def system_config():
    """
    System configuration page.
    """
    return render_template('admin/system.html')

@admin_bp.route('/audit-logs')
@login_required
@admin_required
@audit_action('view_audit_logs')
def audit_logs():
    """
    Audit logs page.
    """
    return render_template('admin/audit_logs.html') 