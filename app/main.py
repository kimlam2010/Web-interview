"""
Main Blueprint for Mekong Recruitment System

This module provides main routes and dashboard functionality following AGENT_RULES_DEVELOPER:
- Dashboard with role-based views
- Basic navigation
- Error handling
- Security middleware
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from typing import Dict, Any

# Import models and utilities
try:
        # Import models
    from app.models import Candidate, Position, AssessmentResult, InterviewEvaluation
    from app.decorators import permission_required, audit_action
    from app.utils import get_candidate_progress, format_currency
except ImportError:
    # Fallback for direct execution
    pass

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
@audit_action('view_dashboard')
def dashboard():
    """
    Main dashboard with role-based views.
    
    Provides different dashboard views based on user role:
    - Admin: Full system overview
    - HR: Candidate management focus
    - Interviewer: Assigned interviews
    - Executive: Hiring decisions
    """
    try:
        # Redirect based on user role
        if current_user.role == 'admin':
            return redirect(url_for('dashboard.admin_dashboard'))
        elif current_user.role == 'hr':
            return redirect(url_for('dashboard.hr_dashboard'))
        elif current_user.role == 'interviewer':
            return redirect(url_for('dashboard.interviewer_dashboard'))
        elif current_user.role in ['cto', 'ceo']:
            return redirect(url_for('dashboard.executive_dashboard'))
        else:
            return render_admin_dashboard()
            
    except Exception as e:
        flash('Error loading dashboard', 'error')
        return render_template('errors/500.html')

def render_admin_dashboard():
    """Render admin dashboard with full system overview."""
    # Get system statistics
    total_candidates = Candidate.query.count()
    pending_candidates = Candidate.query.filter_by(status='pending').count()
    step1_completed = Candidate.query.filter_by(status='step1_completed').count()
    step2_completed = Candidate.query.filter_by(status='step2_completed').count()
    hired_candidates = Candidate.query.filter_by(status='hired').count()
    rejected_candidates = Candidate.query.filter_by(status='rejected').count()
    
    # Get recent activities
    recent_candidates = Candidate.query.order_by(Candidate.created_at.desc()).limit(5).all()
    recent_positions = Position.query.order_by(Position.created_at.desc()).limit(5).all()
    
    # Get assessment statistics
    total_assessments = AssessmentResult.query.count()
    passed_assessments = AssessmentResult.query.filter(AssessmentResult.percentage >= 70).count()
    failed_assessments = AssessmentResult.query.filter(AssessmentResult.percentage < 50).count()
    
    dashboard_data = {
        'total_candidates': total_candidates,
        'pending_candidates': pending_candidates,
        'step1_completed': step1_completed,
        'step2_completed': step2_completed,
        'hired_candidates': hired_candidates,
        'rejected_candidates': rejected_candidates,
        'total_assessments': total_assessments,
        'passed_assessments': passed_assessments,
        'failed_assessments': failed_assessments,
        'recent_candidates': recent_candidates,
        'recent_positions': recent_positions,
        'pass_rate': (passed_assessments / total_assessments * 100) if total_assessments > 0 else 0
    }
    
    return render_template('dashboard/admin.html', data=dashboard_data)

def render_hr_dashboard():
    """Render HR dashboard with candidate management focus."""
    # Get HR-specific statistics
    total_candidates = Candidate.query.count()
    pending_review = Candidate.query.filter_by(status='pending').count()
    manual_review_needed = AssessmentResult.query.filter(
        AssessmentResult.manual_review_required == True
    ).count()
    
    # Get candidates by status
    candidates_by_status = {
        'pending': Candidate.query.filter_by(status='pending').count(),
        'step1_completed': Candidate.query.filter_by(status='step1_completed').count(),
        'step2_completed': Candidate.query.filter_by(status='step2_completed').count(),
        'hired': Candidate.query.filter_by(status='hired').count(),
        'rejected': Candidate.query.filter_by(status='rejected').count()
    }
    
    # Get recent candidates
    recent_candidates = Candidate.query.order_by(Candidate.created_at.desc()).limit(10).all()
    
    # Get positions with active hiring
    active_positions = Position.query.filter_by(is_active=True).all()
    
    dashboard_data = {
        'total_candidates': total_candidates,
        'pending_review': pending_review,
        'manual_review_needed': manual_review_needed,
        'candidates_by_status': candidates_by_status,
        'recent_candidates': recent_candidates,
        'active_positions': active_positions
    }
    
    return render_template('dashboard/hr.html', data=dashboard_data)

def render_interviewer_dashboard():
    """Render interviewer dashboard with assigned interviews."""
    # Get assigned interviews
    assigned_evaluations = InterviewEvaluation.query.filter_by(
        interviewer_id=current_user.id
    ).order_by(InterviewEvaluation.created_at.desc()).limit(10).all()
    
    # Get candidates assigned to this interviewer
    assigned_candidates = Candidate.query.join(InterviewEvaluation).filter(
        InterviewEvaluation.interviewer_id == current_user.id
    ).distinct().all()
    
    # Get pending interviews
    pending_interviews = InterviewEvaluation.query.filter_by(
        interviewer_id=current_user.id,
        recommendation=None
    ).count()
    
    dashboard_data = {
        'assigned_evaluations': assigned_evaluations,
        'assigned_candidates': assigned_candidates,
        'pending_interviews': pending_interviews,
        'total_assigned': len(assigned_candidates)
    }
    
    return render_template('dashboard/interviewer.html', data=dashboard_data)

def render_executive_dashboard():
    """Render executive dashboard with hiring decisions."""
    # Get final interview candidates
    final_candidates = Candidate.query.filter_by(status='step2_completed').all()
    
    # Get recent hiring decisions
    recent_decisions = InterviewEvaluation.query.filter_by(
        step='step3'
    ).order_by(InterviewEvaluation.created_at.desc()).limit(10).all()
    
    # Get hiring statistics
    total_hired = Candidate.query.filter_by(status='hired').count()
    total_rejected = Candidate.query.filter_by(status='rejected').count()
    
    # Get pending executive decisions
    pending_decisions = Candidate.query.filter_by(status='step2_completed').count()
    
    dashboard_data = {
        'final_candidates': final_candidates,
        'recent_decisions': recent_decisions,
        'total_hired': total_hired,
        'total_rejected': total_rejected,
        'pending_decisions': pending_decisions
    }
    
    return render_template('dashboard/executive.html', data=dashboard_data)

@main_bp.route('/profile')
@login_required
@audit_action('view_profile')
def profile():
    """
    User profile page.
    """
    return render_template('main/profile.html', user=current_user)

@main_bp.route('/help')
@login_required
def help_page():
    """
    Help and documentation page.
    """
    return render_template('main/help.html')

@main_bp.route('/about')
def about():
    """
    About page (public access).
    """
    return render_template('main/about.html')

@main_bp.route('/contact')
def contact():
    """
    Contact page (public access).
    """
    return render_template('main/contact.html')

@main_bp.route('/candidates')
@login_required
@permission_required('view_all_candidates')
@audit_action('view_candidates_list')
def candidates():
    """
    Candidates list page.
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('CANDIDATES_PER_PAGE', 20)
        
        # Get filter parameters
        status_filter = request.args.get('status', '')
        position_filter = request.args.get('position', '')
        search_query = request.args.get('search', '')
        
        # Build query
        query = Candidate.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        if position_filter:
            query = query.filter_by(position_id=position_filter)
        
        if search_query:
            query = query.filter(
                Candidate.first_name.contains(search_query) |
                Candidate.last_name.contains(search_query) |
                Candidate.email.contains(search_query)
            )
        
        # Paginate results
        candidates_pagination = query.order_by(Candidate.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get positions for filter
        positions = Position.query.filter_by(is_active=True).all()
        
        return render_template('main/candidates.html',
                             candidates=candidates_pagination.items,
                             pagination=candidates_pagination,
                             positions=positions,
                             filters={
                                 'status': status_filter,
                                 'position': position_filter,
                                 'search': search_query
                             })
        
    except Exception as e:
        flash('Error loading candidates', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/candidates/<int:candidate_id>')
@login_required
@permission_required('view_all_candidates')
@audit_action('view_candidate_detail')
def candidate_detail(candidate_id):
    """
    Candidate detail page.
    """
    try:
        from .models import Candidate
        
        candidate = Candidate.query.get_or_404(candidate_id)
        progress = get_candidate_progress(candidate_id)
        
        # Get assessment results
        assessment_results = AssessmentResult.query.filter_by(
            candidate_id=candidate_id
        ).order_by(AssessmentResult.completed_at.desc()).all()
        
        # Get interview evaluations
        interview_evaluations = InterviewEvaluation.query.filter_by(
            candidate_id=candidate_id
        ).order_by(InterviewEvaluation.created_at.desc()).all()
        
        return render_template('main/candidate_detail.html',
                             candidate=candidate,
                             progress=progress,
                             assessment_results=assessment_results,
                             interview_evaluations=interview_evaluations)
        
    except Exception as e:
        flash('Error loading candidate details', 'error')
        return redirect(url_for('main.candidates'))

@main_bp.route('/positions')
@login_required
@permission_required('view_all_candidates')  # Use same permission for positions
@audit_action('view_positions_list')
def positions():
    """
    Positions list page.
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('CANDIDATES_PER_PAGE', 20)
        
        # Get filter parameters
        department_filter = request.args.get('department', '')
        level_filter = request.args.get('level', '')
        active_filter = request.args.get('active', '')
        
        # Build query
        query = Position.query
        
        if department_filter:
            query = query.filter_by(department=department_filter)
        
        if level_filter:
            query = query.filter_by(level=level_filter)
        
        if active_filter:
            is_active = active_filter == 'true'
            query = query.filter_by(is_active=is_active)
        
        # Paginate results
        positions_pagination = query.order_by(Position.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get departments and levels for filter
        departments = current_app.config.get('POSITION_MANAGEMENT', {}).get('departments', [])
        levels = current_app.config.get('POSITION_MANAGEMENT', {}).get('levels', [])
        
        return render_template('main/positions.html',
                             positions=positions_pagination.items,
                             pagination=positions_pagination,
                             departments=departments,
                             levels=levels,
                             filters={
                                 'department': department_filter,
                                 'level': level_filter,
                                 'active': active_filter
                             })
        
    except Exception as e:
        flash('Error loading positions', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/analytics')
@login_required
@permission_required('view_hiring_analytics')
@audit_action('view_analytics')
def analytics():
    """
    Analytics and reporting page.
    """
    try:
        # Get analytics data
        total_candidates = Candidate.query.count()
        hired_candidates = Candidate.query.filter_by(status='hired').count()
        rejected_candidates = Candidate.query.filter_by(status='rejected').count()
        
        # Get assessment statistics
        total_assessments = AssessmentResult.query.count()
        passed_assessments = AssessmentResult.query.filter(AssessmentResult.percentage >= 70).count()
        failed_assessments = AssessmentResult.query.filter(AssessmentResult.percentage < 50).count()
        
        # Get time-to-hire statistics
        hired_candidates_data = Candidate.query.filter_by(status='hired').all()
        avg_time_to_hire = 0
        if hired_candidates_data:
            total_days = 0
            for candidate in hired_candidates_data:
                # Calculate days from creation to hiring
                if candidate.created_at and candidate.updated_at:
                    days = (candidate.updated_at - candidate.created_at).days
                    total_days += days
            avg_time_to_hire = total_days / len(hired_candidates_data)
        
        analytics_data = {
            'total_candidates': total_candidates,
            'hired_candidates': hired_candidates,
            'rejected_candidates': rejected_candidates,
            'total_assessments': total_assessments,
            'passed_assessments': passed_assessments,
            'failed_assessments': failed_assessments,
            'avg_time_to_hire': round(avg_time_to_hire, 1),
            'hiring_rate': (hired_candidates / total_candidates * 100) if total_candidates > 0 else 0,
            'pass_rate': (passed_assessments / total_assessments * 100) if total_assessments > 0 else 0
        }
        
        return render_template('main/analytics.html', data=analytics_data)
        
    except Exception as e:
        flash('Error loading analytics', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.before_request
def before_request():
    """
    Security middleware for main routes.
    """
    if current_user.is_authenticated:
        # Check session timeout
        last_activity = session.get('last_activity')
        if last_activity:
            last_activity = datetime.fromisoformat(last_activity)
            if datetime.utcnow() - last_activity > timedelta(hours=4):
                flash('Session expired. Please log in again.', 'info')
                return redirect(url_for('auth.login'))
        
        # Update last activity
        session['last_activity'] = datetime.utcnow().isoformat()

@main_bp.after_request
def after_request(response):
    """
    Security headers for main routes.
    """
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response 