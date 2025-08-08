"""
Dashboard Development - Task 7.1
Provides real-time recruitment analytics and performance metrics
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from .models import db, Candidate, Position, AssessmentResult, InterviewEvaluation, ExecutiveDecision, User
from .decorators import hr_required, admin_required, interviewer_required
from sqlalchemy.orm import joinedload
from app.utils import log_activity

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def main_dashboard():
    """Main dashboard with role-specific views."""
    try:
        if current_user.role == 'admin':
            return admin_dashboard()
        elif current_user.role == 'hr':
            return hr_dashboard()
        elif current_user.role in ['cto', 'ceo']:
            return executive_dashboard()
        elif current_user.role == 'interviewer':
            return interviewer_dashboard()
        else:
            return basic_dashboard()
    except Exception as e:
        log_activity(current_user.id, 'error', f'Dashboard error: {str(e)}')
        return render_template('errors/500.html')


@dashboard_bp.route('/hr')
@login_required
@hr_required
def hr_dashboard():
    """HR-specific dashboard with recruitment metrics."""
    try:
        # Get recruitment pipeline data
        pipeline_data = get_recruitment_pipeline()
        
        # Get performance metrics
        performance_metrics = get_performance_metrics()
        
        # Get recent activities
        recent_activities = get_recent_activities()
        
        # Get position analytics
        position_analytics = get_position_analytics()
        
        return render_template('dashboard/hr_dashboard.html',
                             pipeline_data=pipeline_data,
                             performance_metrics=performance_metrics,
                             recent_activities=recent_activities,
                             position_analytics=position_analytics)
    except Exception as e:
        log_activity(current_user.id, 'error', f'HR dashboard error: {str(e)}')
        return render_template('errors/500.html')


@dashboard_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard with system-wide analytics."""
    try:
        # Get system statistics
        system_stats = get_system_statistics()
        
        # Get user activity
        user_activity = get_user_activity()
        
        # Get security metrics
        security_metrics = get_security_metrics()
        
        # Get performance data
        performance_data = get_performance_data()
        
        # Prepare data for template
        data = {
            'total_candidates': system_stats.get('total_candidates', 0),
            'hired_candidates': system_stats.get('hired_candidates', 0),
            'pending_candidates': system_stats.get('pending_candidates', 0),
            'pass_rate': system_stats.get('pass_rate', 0),
            'recent_candidates': user_activity.get('recent_candidates', []),
            'recent_positions': Position.query.order_by(Position.created_at.desc()).limit(5).all(),
            'system_stats': system_stats,
            'user_activity': user_activity,
            'security_metrics': security_metrics,
            'performance_data': performance_data
        }
        
        return render_template('dashboard/admin.html', data=data)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Admin dashboard error: {str(e)}')
        return render_template('errors/500.html')


@dashboard_bp.route('/executive')
@login_required
def executive_dashboard():
    """Executive dashboard for CTO and CEO."""
    try:
        # Get executive-specific metrics
        executive_metrics = get_executive_metrics()
        
        # Get decision analytics
        decision_analytics = get_decision_analytics()
        
        # Get compensation data
        compensation_data = get_compensation_data()
        # Monthly hires data for mini-chart
        monthly_hires = get_monthly_hires_series()
        
        return render_template('dashboard/executive_dashboard.html',
                             executive_metrics=executive_metrics,
                             decision_analytics=decision_analytics,
                              compensation_data=compensation_data,
                              monthly_hires=monthly_hires)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Executive dashboard error: {str(e)}')
        return render_template('errors/500.html')


@dashboard_bp.route('/interviewer')
@login_required
@interviewer_required
def interviewer_dashboard():
    """Interviewer-specific dashboard."""
    try:
        # Get interviewer metrics
        interviewer_metrics = get_interviewer_metrics()
        
        # Get assigned interviews
        assigned_interviews = get_assigned_interviews()
        
        # Get evaluation history
        evaluation_history = get_evaluation_history()
        
        return render_template(
            'dashboard/interviewer_dashboard.html',
            interviewer_metrics=interviewer_metrics,
            assigned_interviews=assigned_interviews,
            evaluation_history=evaluation_history,
        )
    except Exception as e:
        log_activity(current_user.id, 'error', f'Interviewer dashboard error: {str(e)}')
        return render_template('errors/500.html')


@dashboard_bp.route('/interviewer/assigned.json')
@login_required
@interviewer_required
def interviewer_assigned_json():
    """API: danh sách nhiệm vụ đã phân công cho interviewer (chưa hoàn tất)."""
    try:
        search = (request.args.get('search') or '').strip()
        page = max(int(request.args.get('page', 1)), 1)
        size = min(max(int(request.args.get('size', 10)), 1), 50)

        base_query = (
            InterviewEvaluation.query.options(
                joinedload(InterviewEvaluation.candidate).joinedload(Candidate.position)
            )
            .filter(
                InterviewEvaluation.interviewer_id == current_user.id,
                InterviewEvaluation.recommendation.is_(None),
            )
            .order_by(InterviewEvaluation.created_at.desc())
        )

        if search:
            like = f"%{search.lower()}%"
            base_query = base_query.join(Candidate).join(Position).filter(
                db.or_(
                    db.func.lower(Candidate.first_name).like(like),
                    db.func.lower(Candidate.last_name).like(like),
                    db.func.lower(Candidate.email).like(like),
                    db.func.lower(Position.title).like(like),
                )
            )

        total = base_query.count()
        items = (
            base_query.offset((page - 1) * size).limit(size).all()
        )

        def to_item(ev: InterviewEvaluation):
            candidate = ev.candidate
            position = candidate.position if candidate else None
            return {
                'id': ev.id,
                'candidate_name': candidate.get_full_name() if candidate else '-',
                'candidate_email': candidate.email if candidate else '-',
                'position': position.title if position else '-',
                'step': ev.step,
                'created_at': ev.created_at.isoformat() if ev.created_at else None,
            }

        return jsonify({
            'items': [to_item(ev) for ev in items],
            'page': page,
            'total': total,
            'page_size': size,
        })
    except Exception as e:
        log_activity(current_user.id, 'error', f'Assigned JSON error: {str(e)}')
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/interviewer/history.json')
@login_required
@interviewer_required
def interviewer_history_json():
    """API: lịch sử đánh giá của interviewer (đã hoàn tất)."""
    try:
        search = (request.args.get('search') or '').strip()
        page = max(int(request.args.get('page', 1)), 1)
        size = min(max(int(request.args.get('size', 10)), 1), 50)
        from_date = request.args.get('from')
        to_date = request.args.get('to')

        base_query = (
            InterviewEvaluation.query.options(
                joinedload(InterviewEvaluation.candidate).joinedload(Candidate.position)
            )
            .filter(
                InterviewEvaluation.interviewer_id == current_user.id,
                InterviewEvaluation.recommendation.isnot(None),
            )
            .order_by(InterviewEvaluation.created_at.desc())
        )

        if from_date:
            try:
                dt_from = datetime.fromisoformat(from_date)
                base_query = base_query.filter(InterviewEvaluation.created_at >= dt_from)
            except Exception:
                pass
        if to_date:
            try:
                dt_to = datetime.fromisoformat(to_date)
                base_query = base_query.filter(InterviewEvaluation.created_at <= dt_to)
            except Exception:
                pass

        if search:
            like = f"%{search.lower()}%"
            base_query = base_query.join(Candidate).join(Position).filter(
                db.or_(
                    db.func.lower(Candidate.first_name).like(like),
                    db.func.lower(Candidate.last_name).like(like),
                    db.func.lower(Candidate.email).like(like),
                    db.func.lower(Position.title).like(like),
                )
            )

        total = base_query.count()
        items = (
            base_query.offset((page - 1) * size).limit(size).all()
        )

        def to_item(ev: InterviewEvaluation):
            candidate = ev.candidate
            position = candidate.position if candidate else None
            return {
                'id': ev.id,
                'candidate_name': candidate.get_full_name() if candidate else '-',
                'position': position.title if position else '-',
                'score': ev.score,
                'recommendation': ev.recommendation,
                'created_at': ev.created_at.isoformat() if ev.created_at else None,
            }

        return jsonify({
            'items': [to_item(ev) for ev in items],
            'page': page,
            'total': total,
            'page_size': size,
        })
    except Exception as e:
        log_activity(current_user.id, 'error', f'History JSON error: {str(e)}')
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/pipeline-data')
@login_required
@hr_required
def api_pipeline_data():
    """API endpoint for recruitment pipeline data."""
    try:
        pipeline_data = get_recruitment_pipeline()
        return jsonify(pipeline_data)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Pipeline data API error: {str(e)}')
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/performance-metrics')
@login_required
@hr_required
def api_performance_metrics():
    """API endpoint for performance metrics."""
    try:
        metrics = get_performance_metrics()
        return jsonify(metrics)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Performance metrics API error: {str(e)}')
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/time-to-hire')
@login_required
@hr_required
def api_time_to_hire():
    """API endpoint for time-to-hire analytics."""
    try:
        time_to_hire_data = calculate_time_to_hire()
        return jsonify(time_to_hire_data)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Time-to-hire API error: {str(e)}')
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/pass-rate-analytics')
@login_required
@hr_required
def api_pass_rate_analytics():
    """API endpoint for pass rate analytics."""
    try:
        pass_rate_data = calculate_pass_rates()
        return jsonify(pass_rate_data)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Pass rate API error: {str(e)}')
        return jsonify({'error': str(e)}), 500


# Helper functions

def get_recruitment_pipeline():
    """Get recruitment pipeline data."""
    try:
        # Get candidates by status
        total_candidates = Candidate.query.count()
        pending_candidates = Candidate.query.filter_by(status='pending').count()
        step1_completed = Candidate.query.filter_by(status='step1_completed').count()
        step2_completed = Candidate.query.filter_by(status='step2_completed').count()
        hired_candidates = Candidate.query.filter_by(status='hired').count()
        rejected_candidates = Candidate.query.filter_by(status='rejected').count()
        
        # Calculate percentages
        pipeline_data = {
            'total': total_candidates,
            'pending': {
                'count': pending_candidates,
                'percentage': (pending_candidates / total_candidates * 100) if total_candidates > 0 else 0
            },
            'step1_completed': {
                'count': step1_completed,
                'percentage': (step1_completed / total_candidates * 100) if total_candidates > 0 else 0
            },
            'step2_completed': {
                'count': step2_completed,
                'percentage': (step2_completed / total_candidates * 100) if total_candidates > 0 else 0
            },
            'hired': {
                'count': hired_candidates,
                'percentage': (hired_candidates / total_candidates * 100) if total_candidates > 0 else 0
            },
            'rejected': {
                'count': rejected_candidates,
                'percentage': (rejected_candidates / total_candidates * 100) if total_candidates > 0 else 0
            }
        }
        
        return pipeline_data
    except Exception as e:
        log_activity(current_user.id, 'error', f'Pipeline data error: {str(e)}')
        return {}


def get_performance_metrics():
    """Get performance metrics."""
    try:
        # Calculate pass rates
        step1_results = AssessmentResult.query.filter_by(step='step1').all()
        step1_passed = len([r for r in step1_results if r.percentage >= 70])
        step1_pass_rate = (step1_passed / len(step1_results) * 100) if step1_results else 0
        
        # Step 2 pass rate (completed = có recommendation)
        step2_evaluations = InterviewEvaluation.query.filter(InterviewEvaluation.step == 'step2').all()
        completed_step2 = [e for e in step2_evaluations if e.recommendation is not None]
        step2_passed = len([e for e in completed_step2 if (e.score or 0) >= 7])
        step2_pass_rate = (step2_passed / len(completed_step2) * 100) if completed_step2 else 0
        
        # Executive decisions
        executive_decisions = ExecutiveDecision.query.filter_by(status='completed').all()
        hire_decisions = len([d for d in executive_decisions if d.final_decision == 'hire'])
        hire_rate = (hire_decisions / len(executive_decisions) * 100) if executive_decisions else 0
        
        # Time metrics
        avg_time_to_hire = calculate_average_time_to_hire()
        
        return {
            'step1_pass_rate': step1_pass_rate,
            'step2_pass_rate': step2_pass_rate,
            'hire_rate': hire_rate,
            'avg_time_to_hire': avg_time_to_hire,
            'total_candidates': Candidate.query.count(),
            'active_positions': Position.query.filter_by(is_active=True).count()
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Performance metrics error: {str(e)}')
        return {}


def get_recent_activities():
    """Get recent activities for dashboard."""
    try:
        # Get recent candidates
        recent_candidates = Candidate.query.order_by(Candidate.created_at.desc()).limit(5).all()
        
        # Get recent assessments
        recent_assessments = AssessmentResult.query.order_by(AssessmentResult.completed_at.desc()).limit(5).all()
        
        # Get recent interviews
        recent_interviews = InterviewEvaluation.query.order_by(InterviewEvaluation.created_at.desc()).limit(5).all()
        
        return {
            'recent_candidates': recent_candidates,
            'recent_assessments': recent_assessments,
            'recent_interviews': recent_interviews
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Recent activities error: {str(e)}')
        return {}


def get_position_analytics():
    """Get position-specific analytics."""
    try:
        positions = Position.query.filter_by(is_active=True).all()
        position_data = []
        
        for position in positions:
            candidates = Candidate.query.filter_by(position_id=position.id).all()
            hired_count = len([c for c in candidates if c.status == 'hired'])
            
            position_data.append({
                'position': position,
                'total_candidates': len(candidates),
                'hired_count': hired_count,
                'hire_rate': (hired_count / len(candidates) * 100) if candidates else 0
            })
        
        return position_data
    except Exception as e:
        log_activity(current_user.id, 'error', f'Position analytics error: {str(e)}')
        return []


def get_system_statistics():
    """Get system-wide statistics for admin."""
    try:
        # Get basic counts
        total_candidates = Candidate.query.count()
        total_positions = Position.query.count()
        total_assessments = AssessmentResult.query.count()
        
        # Calculate pass rate
        passed_assessments = AssessmentResult.query.filter(AssessmentResult.percentage >= 70).count()
        pass_rate = (passed_assessments / total_assessments * 100) if total_assessments > 0 else 0
        
        # Get hired candidates (those with executive decisions)
        hired_candidates = ExecutiveDecision.query.filter_by(status='completed', final_decision='hire').count()
        
        # Get pending candidates (those in assessment or interview stage)
        pending_candidates = Candidate.query.filter(
            Candidate.status.in_(['pending', 'step1_completed', 'step2_completed'])
        ).count()
        
        return {
            'total_users': User.query.count(),
            'total_candidates': total_candidates,
            'hired_candidates': hired_candidates,
            'pending_candidates': pending_candidates,
            'pass_rate': pass_rate,
            'total_positions': total_positions,
            'total_assessments': total_assessments,
            'total_interviews': InterviewEvaluation.query.count(),
            'total_decisions': ExecutiveDecision.query.count()
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'System statistics error: {str(e)}')
        return {
            'total_users': 0,
            'total_candidates': 0,
            'hired_candidates': 0,
            'pending_candidates': 0,
            'pass_rate': 0,
            'total_positions': 0,
            'total_assessments': 0,
            'total_interviews': 0,
            'total_decisions': 0
        }


def get_user_activity():
    """Get user activity data."""
    try:
        # Get recent logins
        recent_logins = User.query.filter(User.last_login.isnot(None)).order_by(User.last_login.desc()).limit(10).all()
        
        # Get user roles distribution
        role_counts = db.session.query(User.role, db.func.count(User.id)).group_by(User.role).all()
        
        # Get recent candidates
        recent_candidates = Candidate.query.order_by(Candidate.created_at.desc()).limit(5).all()
        
        return {
            'recent_logins': recent_logins,
            'role_distribution': dict(role_counts),
            'recent_candidates': recent_candidates
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'User activity error: {str(e)}')
        return {
            'recent_logins': [],
            'role_distribution': {},
            'recent_candidates': []
        }


def get_security_metrics():
    """Get security-related metrics."""
    try:
        # Get locked accounts
        locked_accounts = User.query.filter(User.locked_until > datetime.utcnow()).count()
        
        # Get failed login attempts
        failed_attempts = User.query.filter(User.login_attempts > 0).count()
        
        return {
            'locked_accounts': locked_accounts,
            'failed_attempts': failed_attempts,
            'security_score': calculate_security_score()
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Security metrics error: {str(e)}')
        return {}


def get_performance_data():
    """Get system performance data."""
    try:
        # Calculate response times (placeholder)
        avg_response_time = 0.5  # seconds
        
        # Get database performance
        db_performance = {
            'avg_query_time': 0.1,
            'slow_queries': 0,
            'connection_pool': 0.8
        }
        
        return {
            'avg_response_time': avg_response_time,
            'db_performance': db_performance,
            'uptime': 99.9
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Performance data error: {str(e)}')
        return {}


def get_executive_metrics():
    """Get executive-specific metrics."""
    try:
        if current_user.role == 'cto':
            # CTO metrics
            technical_decisions = ExecutiveDecision.query.filter_by(cto_id=current_user.id).count()
            pending_decisions = ExecutiveDecision.query.filter_by(cto_id=None).count()
            
            return {
                'technical_decisions': technical_decisions,
                'pending_decisions': pending_decisions,
                'avg_technical_score': calculate_avg_technical_score()
            }
        elif current_user.role == 'ceo':
            # CEO metrics
            cultural_decisions = ExecutiveDecision.query.filter_by(ceo_id=current_user.id).count()
            pending_decisions = ExecutiveDecision.query.filter_by(ceo_id=None).count()
            
            return {
                'cultural_decisions': cultural_decisions,
                'pending_decisions': pending_decisions,
                'avg_cultural_score': calculate_avg_cultural_score()
            }
        else:
            return {}
    except Exception as e:
        log_activity(current_user.id, 'error', f'Executive metrics error: {str(e)}')
        return {}


def get_decision_analytics():
    """Get decision analytics."""
    try:
        decisions = ExecutiveDecision.query.all()
        
        # Calculate decision statistics
        total_decisions = len(decisions)
        completed_decisions = len([d for d in decisions if d.status == 'completed'])
        hire_decisions = len([d for d in decisions if d.final_decision == 'hire'])
        
        return {
            'total_decisions': total_decisions,
            'completed_decisions': completed_decisions,
            'hire_decisions': hire_decisions,
            'hire_rate': (hire_decisions / completed_decisions * 100) if completed_decisions > 0 else 0
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Decision analytics error: {str(e)}')
        return {}


def get_compensation_data():
    """Get compensation approval data."""
    try:
        compensation_approvals = ExecutiveDecision.query.filter_by(compensation_status='approved').count()
        pending_approvals = ExecutiveDecision.query.filter_by(compensation_status='pending').count()
        
        return {
            'compensation_approvals': compensation_approvals,
            'pending_approvals': pending_approvals
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Compensation data error: {str(e)}')
        return {}


def get_monthly_hires_series():
    """Aggregate hires theo tháng trong 12 tháng gần nhất."""
    try:
        from datetime import date
        # Giả định Decision.completed_at là ngày hoàn tất; fallback created_at nếu không có
        rows = db.session.query(
            db.func.strftime('%Y-%m', ExecutiveDecision.completed_at),
            db.func.count(ExecutiveDecision.id)
        ).filter(
            ExecutiveDecision.status == 'completed',
            ExecutiveDecision.final_decision == 'hire',
            ExecutiveDecision.completed_at.isnot(None)
        ).group_by(db.func.strftime('%Y-%m', ExecutiveDecision.completed_at)).order_by(db.func.strftime('%Y-%m', ExecutiveDecision.completed_at)).all()

        labels = []
        values = []
        for ym, cnt in rows:
            labels.append(ym or '')
            values.append(int(cnt or 0))
        return { 'labels': labels, 'values': values }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Monthly hires series error: {str(e)}')
        return { 'labels': [], 'values': [] }


def get_interviewer_metrics():
    """Get interviewer-specific metrics."""
    try:
        # Get interviewer's evaluations
        evaluations = InterviewEvaluation.query.filter_by(interviewer_id=current_user.id).all()
        
        total_evaluations = len(evaluations)
        completed_evaluations = len([e for e in evaluations if e.recommendation is not None])
        avg_score = round((sum((e.score or 0) for e in evaluations) / len(evaluations)) if evaluations else 0, 2)
        
        return {
            'total_evaluations': total_evaluations,
            'completed_evaluations': completed_evaluations,
            'avg_score': avg_score,
            'completion_rate': (completed_evaluations / total_evaluations * 100) if total_evaluations > 0 else 0
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Interviewer metrics error: {str(e)}')
        return {}


def get_assigned_interviews():
    """Get assigned interviews for interviewer."""
    try:
        return InterviewEvaluation.query.filter(
            InterviewEvaluation.interviewer_id == current_user.id,
            InterviewEvaluation.recommendation.is_(None)
        ).join(Candidate).all()
    except Exception as e:
        log_activity(current_user.id, 'error', f'Assigned interviews error: {str(e)}')
        return []


def get_evaluation_history():
    """Get evaluation history for interviewer."""
    try:
        return InterviewEvaluation.query.filter(
            InterviewEvaluation.interviewer_id == current_user.id,
            InterviewEvaluation.recommendation.isnot(None)
        ).join(Candidate).order_by(InterviewEvaluation.created_at.desc()).limit(10).all()
    except Exception as e:
        log_activity(current_user.id, 'error', f'Evaluation history error: {str(e)}')
        return []


def calculate_time_to_hire():
    """Calculate time-to-hire analytics."""
    try:
        hired_candidates = Candidate.query.filter_by(status='hired').all()
        time_to_hire_data = []
        
        for candidate in hired_candidates:
            # Calculate time from creation to hire
            created_at = candidate.created_at
            # Assuming hire date is stored somewhere or use current date
            hire_date = datetime.utcnow()  # Placeholder
            days_to_hire = (hire_date - created_at).days
            
            time_to_hire_data.append({
                'candidate_id': candidate.id,
                'candidate_name': candidate.get_full_name(),
                'position': candidate.position.title,
                'days_to_hire': days_to_hire
            })
        
        avg_days = sum(d['days_to_hire'] for d in time_to_hire_data) / len(time_to_hire_data) if time_to_hire_data else 0
        
        return {
            'time_to_hire_data': time_to_hire_data,
            'average_days': avg_days,
            'min_days': min(d['days_to_hire'] for d in time_to_hire_data) if time_to_hire_data else 0,
            'max_days': max(d['days_to_hire'] for d in time_to_hire_data) if time_to_hire_data else 0
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Time-to-hire calculation error: {str(e)}')
        return {}


def calculate_pass_rates():
    """Calculate pass rates by step and position."""
    try:
        # Step 1 pass rates
        step1_results = AssessmentResult.query.filter_by(step='step1').all()
        step1_pass_rate = len([r for r in step1_results if r.percentage >= 70]) / len(step1_results) * 100 if step1_results else 0
        
        # Step 2 pass rates
        step2_evaluations = InterviewEvaluation.query.filter(InterviewEvaluation.step == 'step2').all()
        completed_step2 = [e for e in step2_evaluations if e.recommendation is not None]
        step2_pass_rate = (len([e for e in completed_step2 if (e.score or 0) >= 7]) / len(completed_step2) * 100) if completed_step2 else 0
        
        # Position-specific pass rates
        positions = Position.query.all()
        position_pass_rates = {}
        
        for position in positions:
            candidates = Candidate.query.filter_by(position_id=position.id).all()
            if candidates:
                hired_count = len([c for c in candidates if c.status == 'hired'])
                position_pass_rates[position.title] = (hired_count / len(candidates)) * 100
        
        return {
            'step1_pass_rate': step1_pass_rate,
            'step2_pass_rate': step2_pass_rate,
            'position_pass_rates': position_pass_rates
        }
    except Exception as e:
        log_activity(current_user.id, 'error', f'Pass rate calculation error: {str(e)}')
        return {}


def calculate_average_time_to_hire():
    """Calculate average time to hire."""
    try:
        # Placeholder calculation
        return 15  # days
    except Exception as e:
        log_activity(current_user.id, 'error', f'Average time to hire error: {str(e)}')
        return 0


def calculate_security_score():
    """Calculate security score."""
    try:
        # Placeholder calculation
        return 85  # percentage
    except Exception as e:
        log_activity(current_user.id, 'error', f'Security score error: {str(e)}')
        return 0


def calculate_avg_technical_score():
    """Calculate average technical score for CTO."""
    try:
        cto_decisions = ExecutiveDecision.query.filter_by(cto_id=current_user.id).all()
        if cto_decisions:
            return sum(d.cto_score for d in cto_decisions if d.cto_score) / len(cto_decisions)
        return 0
    except Exception as e:
        log_activity(current_user.id, 'error', f'Average technical score error: {str(e)}')
        return 0


def calculate_avg_cultural_score():
    """Calculate average cultural score for CEO."""
    try:
        ceo_decisions = ExecutiveDecision.query.filter_by(ceo_id=current_user.id).all()
        if ceo_decisions:
            return sum(d.ceo_score for d in ceo_decisions if d.ceo_score) / len(ceo_decisions)
        return 0
    except Exception as e:
        log_activity(current_user.id, 'error', f'Average cultural score error: {str(e)}')
        return 0


def basic_dashboard():
    """Basic dashboard for users without specific role."""
    try:
        return render_template('dashboard/basic_dashboard.html')
    except Exception as e:
        log_activity(current_user.id, 'error', f'Basic dashboard error: {str(e)}')
        return render_template('errors/500.html')