"""
HR Blueprint for Mekong Recruitment System

This module provides HR functionality following AGENT_RULES_DEVELOPER:
- Candidate management with CRUD operations
- Position management
- Assessment coordination
- Interview scheduling
- Search and filtering capabilities
- Bulk operations
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SelectField, TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from typing import List, Dict, Any

from . import db
from .models import Candidate, Position, User, AuditLog
from .decorators import hr_required, audit_action
from app.utils import log_audit_event, get_client_ip
from .candidate_auth import create_candidate_credentials

# Create blueprint
hr_bp = Blueprint('hr', __name__)

# Forms
class CandidateForm(FlaskForm):
    """Form for adding/editing candidates."""
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=10, max=20)])
    position_id = SelectField('Position', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    cv_file = FileField('CV File', validators=[Optional()])
    submit = SubmitField('Save Candidate')

class CandidateSearchForm(FlaskForm):
    """Form for candidate search and filtering."""
    search_term = StringField('Search', validators=[Optional()])
    position_filter = SelectField('Position', coerce=int, validators=[Optional()])
    status_filter = SelectField('Status', validators=[Optional()])
    date_from = StringField('From Date', validators=[Optional()])
    date_to = StringField('To Date', validators=[Optional()])

@hr_bp.route('/')
@login_required
@hr_required
@audit_action('view_hr_dashboard')
def hr_dashboard():
    """
    HR dashboard with key metrics.
    """
    # Get dashboard statistics
    total_candidates = Candidate.query.count()
    pending_candidates = Candidate.query.filter_by(status='pending').count()
    step1_completed = Candidate.query.filter_by(status='step1_completed').count()
    step2_completed = Candidate.query.filter_by(status='step2_completed').count()
    hired_candidates = Candidate.query.filter_by(status='hired').count()
    
    # Recent candidates
    recent_candidates = Candidate.query.order_by(Candidate.created_at.desc()).limit(5).all()
    
    return render_template('hr/dashboard.html', 
                         total_candidates=total_candidates,
                         pending_candidates=pending_candidates,
                         step1_completed=step1_completed,
                         step2_completed=step2_completed,
                         hired_candidates=hired_candidates,
                         recent_candidates=recent_candidates)

@hr_bp.route('/candidates')
@login_required
@hr_required
@audit_action('view_candidate_management')
def candidate_management():
    """
    Candidate management page with search and filtering.
    """
    form = CandidateSearchForm()
    
    # Get filter parameters
    search_term = request.args.get('search_term', '')
    position_filter = request.args.get('position_filter', '')
    status_filter = request.args.get('status_filter', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query
    query = Candidate.query
    
    # Apply filters
    if search_term:
        query = query.filter(
            db.or_(
                Candidate.first_name.ilike(f'%{search_term}%'),
                Candidate.last_name.ilike(f'%{search_term}%'),
                Candidate.email.ilike(f'%{search_term}%'),
                Candidate.phone.ilike(f'%{search_term}%')
            )
        )
    
    if position_filter:
        query = query.filter(Candidate.position_id == position_filter)
    
    if status_filter:
        query = query.filter(Candidate.status == status_filter)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Candidate.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Candidate.created_at <= to_date)
        except ValueError:
            pass
    
    # Get paginated results
    candidates = query.order_by(Candidate.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get positions for filter dropdown
    positions = Position.query.filter_by(is_active=True).all()
    
    return render_template('hr/candidates.html',
                         candidates=candidates,
                         form=form,
                         positions=positions,
                         search_term=search_term,
                         position_filter=position_filter,
                         status_filter=status_filter,
                         date_from=date_from,
                         date_to=date_to)

@hr_bp.route('/candidates/add', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('add_candidate')
def add_candidate():
    """
    Add new candidate with CV upload.
    """
    form = CandidateForm()
    form.position_id.choices = [(p.id, p.title) for p in Position.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # Handle CV file upload
        cv_filename = None
        if form.cv_file.data:
            file = form.cv_file.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                cv_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file.save(os.path.join('uploads', 'cv', cv_filename))
        
        # Create candidate
        candidate = Candidate(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            position_id=form.position_id.data,
            notes=form.notes.data,
            cv_filename=cv_filename,
            created_by=current_user.id
        )
        
        db.session.add(candidate)
        db.session.commit()
        
        # Create temporary credentials
        username, password = create_candidate_credentials(candidate)
        
        flash(f'Candidate added successfully. Username: {username}, Password: {password}', 'success')
        return redirect(url_for('hr.candidate_management'))
    
    return render_template('hr/add_candidate.html', form=form)

@hr_bp.route('/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('edit_candidate')
def edit_candidate(candidate_id):
    """
    Edit candidate information.
    """
    candidate = Candidate.query.get_or_404(candidate_id)
    form = CandidateForm(obj=candidate)
    form.position_id.choices = [(p.id, p.title) for p in Position.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        candidate.first_name = form.first_name.data
        candidate.last_name = form.last_name.data
        candidate.email = form.email.data
        candidate.phone = form.phone.data
        candidate.position_id = form.position_id.data
        candidate.notes = form.notes.data
        
        # Handle CV file upload
        if form.cv_file.data:
            file = form.cv_file.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                cv_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file.save(os.path.join('uploads', 'cv', cv_filename))
                candidate.cv_filename = cv_filename
        
        db.session.commit()
        flash('Candidate updated successfully.', 'success')
        return redirect(url_for('hr.candidate_management'))
    
    return render_template('hr/edit_candidate.html', form=form, candidate=candidate)

@hr_bp.route('/candidates/<int:candidate_id>/delete', methods=['POST'])
@login_required
@hr_required
@audit_action('delete_candidate')
def delete_candidate(candidate_id):
    """
    Delete candidate.
    """
    candidate = Candidate.query.get_or_404(candidate_id)
    
    # Delete CV file if exists
    if candidate.cv_filename:
        cv_path = os.path.join('uploads', 'cv', candidate.cv_filename)
        if os.path.exists(cv_path):
            os.remove(cv_path)
    
    db.session.delete(candidate)
    db.session.commit()
    
    flash('Candidate deleted successfully.', 'success')
    return redirect(url_for('hr.candidate_management'))

@hr_bp.route('/candidates/bulk-delete', methods=['POST'])
@login_required
@hr_required
@audit_action('bulk_delete_candidates')
def bulk_delete_candidates():
    """
    Bulk delete candidates.
    """
    candidate_ids = request.form.getlist('candidate_ids')
    
    if not candidate_ids:
        flash('No candidates selected.', 'error')
        return redirect(url_for('hr.candidate_management'))
    
    deleted_count = 0
    for candidate_id in candidate_ids:
        candidate = Candidate.query.get(candidate_id)
        if candidate:
            # Delete CV file if exists
            if candidate.cv_filename:
                cv_path = os.path.join('uploads', 'cv', candidate.cv_filename)
                if os.path.exists(cv_path):
                    os.remove(cv_path)
            
            db.session.delete(candidate)
            deleted_count += 1
    
    db.session.commit()
    flash(f'{deleted_count} candidates deleted successfully.', 'success')
    return redirect(url_for('hr.candidate_management'))

@hr_bp.route('/candidates/<int:candidate_id>/credentials', methods=['POST'])
@login_required
@hr_required
@audit_action('regenerate_candidate_credentials')
def regenerate_credentials(candidate_id):
    """
    Regenerate candidate credentials.
    """
    candidate = Candidate.query.get_or_404(candidate_id)
    
    # Create new credentials
    username, password = create_candidate_credentials(candidate)
    
    flash(f'New credentials generated. Username: {username}, Password: {password}', 'success')
    return redirect(url_for('hr.candidate_management'))

@hr_bp.route('/candidates/export')
@login_required
@hr_required
@audit_action('export_candidates')
def export_candidates():
    """
    Export candidates to CSV.
    """
    # Implementation for CSV export
    pass

@hr_bp.route('/candidates/import', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('import_candidates')
def import_candidates():
    """
    Import candidates from CSV.
    """
    # Implementation for CSV import
    pass

@hr_bp.route('/positions')
@login_required
@hr_required
@audit_action('view_position_management')
def position_management():
    """
    Position management page.
    """
    return render_template('hr/positions.html')

@hr_bp.route('/assessments')
@login_required
@hr_required
@audit_action('view_assessment_management')
def assessment_management():
    """
    Assessment management page.
    """
    return render_template('hr/assessments.html')

@hr_bp.route('/interviews')
@login_required
@hr_required
@audit_action('view_interview_scheduling')
def interview_scheduling():
    """
    Interview scheduling page.
    """
    return render_template('hr/interviews.html') 

# Helper functions
def allowed_file(filename: str) -> bool:
    """
    Check if file extension is allowed.
    
    Args:
        filename (str): Filename to check
        
    Returns:
        bool: True if allowed
    """
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS 