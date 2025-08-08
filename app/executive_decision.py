"""
Executive Decision System - Task 6.2
Manages Step 3 final interview decisions with CTO and CEO approval workflow
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.exceptions import Forbidden
from datetime import datetime
import json

from .models import db, Candidate, Position, Step1Question, Step2Question, Step3Question, InterviewEvaluation, AssessmentResult, User, ExecutiveDecision
from .decorators import hr_required, executive_required, admin_required
from app.utils import log_activity, send_email

executive_decision_bp = Blueprint('executive_decision', __name__)


@executive_decision_bp.route('/dashboard')
@login_required
@executive_required
def executive_dashboard():
    """Executive dashboard for CTO and CEO."""
    try:
        # Get candidates ready for Step 3 (passed Step 2)
        candidates_ready = get_candidates_ready_for_step3()
        
        # Get pending decisions
        pending_decisions = ExecutiveDecision.query.filter_by(
            status='pending'
        ).join(Candidate).all()
        
        # Get completed decisions
        completed_decisions = ExecutiveDecision.query.filter_by(
            status='completed'
        ).join(Candidate).order_by(ExecutiveDecision.completed_at.desc()).limit(10).all()
        
        return render_template('executive/dashboard.html',
                             candidates_ready=candidates_ready,
                             pending_decisions=pending_decisions,
                             completed_decisions=completed_decisions)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Executive dashboard error: {str(e)}')
        flash('Có lỗi xảy ra khi tải dashboard.', 'error')
        return redirect(url_for('main.dashboard'))


@executive_decision_bp.route('/candidate/<int:candidate_id>/evaluate')
@login_required
@executive_required
def evaluate_candidate(candidate_id):
    """Evaluate candidate for final decision."""
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        position = Position.query.get(candidate.position_id)
        
        # Check if candidate is ready for Step 3
        if not is_candidate_ready_for_step3(candidate_id):
            flash('Ứng viên chưa sẵn sàng cho Step 3.', 'warning')
            return redirect(url_for('executive_decision.executive_dashboard'))
        
        # Get Step 1 and Step 2 results
        step1_result = AssessmentResult.query.filter_by(
            candidate_id=candidate_id, step=1
        ).first()
        
        step2_evaluations = InterviewEvaluation.query.filter_by(
            candidate_id=candidate_id, status='completed'
        ).all()
        
        # Get existing decision if any
        existing_decision = ExecutiveDecision.query.filter_by(
            candidate_id=candidate_id
        ).first()
        
        return render_template('executive/evaluate_candidate.html',
                             candidate=candidate,
                             position=position,
                             step1_result=step1_result,
                             step2_evaluations=step2_evaluations,
                             existing_decision=existing_decision)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Candidate evaluation error: {str(e)}')
        flash('Có lỗi xảy ra khi đánh giá ứng viên.', 'error')
        return redirect(url_for('executive_decision.executive_dashboard'))


@executive_decision_bp.route('/candidate/<int:candidate_id>/submit-decision', methods=['POST'])
@login_required
@executive_required
def submit_decision(candidate_id):
    """Submit executive decision for candidate."""
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        
        # Get decision data
        technical_score = float(request.form.get('technical_score', 0))
        cultural_score = float(request.form.get('cultural_score', 0))
        leadership_score = float(request.form.get('leadership_score', 0))
        overall_recommendation = request.form.get('overall_recommendation')
        notes = request.form.get('notes', '')
        
        # Calculate weighted score based on role
        if current_user.role == 'cto':
            weighted_score = technical_score * 0.6 + cultural_score * 0.4
            decision_type = 'cto'
        elif current_user.role == 'ceo':
            weighted_score = technical_score * 0.4 + cultural_score * 0.6
            decision_type = 'ceo'
        else:
            return jsonify({'success': False, 'error': 'Invalid role for decision'})
        
        # Create or update decision
        decision = ExecutiveDecision.query.filter_by(
            candidate_id=candidate_id
        ).first()
        
        if not decision:
            decision = ExecutiveDecision(
                candidate_id=candidate_id,
                cto_id=None,
                ceo_id=None,
                cto_score=None,
                ceo_score=None,
                cto_recommendation=None,
                ceo_recommendation=None,
                status='pending'
            )
            db.session.add(decision)
        
        # Update decision based on role
        if decision_type == 'cto':
            decision.cto_id = current_user.id
            decision.cto_score = weighted_score
            decision.cto_recommendation = overall_recommendation
            decision.cto_notes = notes
            decision.cto_evaluated_at = datetime.utcnow()
        else:  # CEO
            decision.ceo_id = current_user.id
            decision.ceo_score = weighted_score
            decision.ceo_recommendation = overall_recommendation
            decision.ceo_notes = notes
            decision.ceo_evaluated_at = datetime.utcnow()
        
        # Check if both decisions are complete
        if decision.cto_id and decision.ceo_id:
            decision.status = 'completed'
            decision.completed_at = datetime.utcnow()
            
            # Calculate final decision
            final_score = (decision.cto_score + decision.ceo_score) / 2
            if final_score >= 7 and decision.cto_recommendation == 'hire' and decision.ceo_recommendation == 'hire':
                decision.final_decision = 'hire'
            elif final_score >= 5:
                decision.final_decision = 'manual_review'
            else:
                decision.final_decision = 'reject'
            
            # Send notification
            send_final_decision_notification(decision)
        
        db.session.commit()
        
        log_activity(current_user.id, 'decision_submitted', 
                    f'Submitted {decision_type.upper()} decision for candidate {candidate_id}')
        
        return jsonify({
            'success': True,
            'message': f'Quyết định {decision_type.upper()} đã được gửi thành công!',
            'weighted_score': weighted_score,
            'decision_complete': decision.status == 'completed'
        })
    except Exception as e:
        log_activity(current_user.id, 'error', f'Decision submission error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@executive_decision_bp.route('/decision/<int:decision_id>/view')
@login_required
@hr_required
def view_decision(decision_id):
    """View executive decision details."""
    try:
        decision = ExecutiveDecision.query.get_or_404(decision_id)
        candidate = Candidate.query.get(decision.candidate_id)
        cto = User.query.get(decision.cto_id) if decision.cto_id else None
        ceo = User.query.get(decision.ceo_id) if decision.ceo_id else None
        
        return render_template('executive/view_decision.html',
                             decision=decision,
                             candidate=candidate,
                             cto=cto,
                             ceo=ceo)
    except Exception as e:
        log_activity(current_user.id, 'error', f'View decision error: {str(e)}')
        flash('Có lỗi xảy ra khi xem quyết định.', 'error')
        return redirect(url_for('executive_decision.executive_dashboard'))


@executive_decision_bp.route('/compensation/<int:candidate_id>/approve', methods=['POST'])
@login_required
@executive_required
def approve_compensation(candidate_id):
    """Approve compensation package for candidate."""
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        
        # Get compensation data
        base_salary = float(request.form.get('base_salary', 0))
        benefits = request.form.get('benefits', '')
        equity = request.form.get('equity', '')
        notes = request.form.get('notes', '')
        
        # Create compensation approval
        decision = ExecutiveDecision.query.filter_by(
            candidate_id=candidate_id
        ).first()
        
        if not decision:
            return jsonify({'success': False, 'error': 'No decision found for candidate'})
        
        if current_user.role == 'cto':
            decision.cto_compensation_approved = True
            decision.cto_compensation_notes = notes
        elif current_user.role == 'ceo':
            decision.ceo_compensation_approved = True
            decision.ceo_compensation_notes = notes
        
        # Check if both approvals are complete
        if decision.cto_compensation_approved and decision.ceo_compensation_approved:
            decision.compensation_status = 'approved'
            decision.compensation_approved_at = datetime.utcnow()
            
            # Send notification
            send_compensation_approval_notification(decision)
        
        db.session.commit()
        
        log_activity(current_user.id, 'compensation_approved', 
                    f'Approved compensation for candidate {candidate_id}')
        
        return jsonify({
            'success': True,
            'message': 'Phê duyệt lương thưởng thành công!',
            'compensation_complete': decision.compensation_status == 'approved'
        })
    except Exception as e:
        log_activity(current_user.id, 'error', f'Compensation approval error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@executive_decision_bp.route('/track-decisions')
@login_required
@hr_required
def track_decisions():
    """Track all executive decisions."""
    try:
        # Get all decisions
        all_decisions = ExecutiveDecision.query.join(Candidate).order_by(
            ExecutiveDecision.created_at.desc()
        ).all()
        
        # Get statistics
        stats = calculate_decision_statistics()
        
        return render_template('executive/track_decisions.html',
                             decisions=all_decisions,
                             stats=stats)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Track decisions error: {str(e)}')
        flash('Có lỗi xảy ra khi theo dõi quyết định.', 'error')
        return redirect(url_for('main.dashboard'))


@executive_decision_bp.route('/notifications')
@login_required
@executive_required
def send_notifications():
    """Send notifications for pending decisions."""
    try:
        # Get pending decisions
        pending_decisions = ExecutiveDecision.query.filter_by(
            status='pending'
        ).join(Candidate).all()
        
        notifications_sent = 0
        for decision in pending_decisions:
            if send_decision_reminder(decision):
                notifications_sent += 1
        
        log_activity(current_user.id, 'notifications_sent', 
                    f'Sent {notifications_sent} decision notifications')
        
        return jsonify({
            'success': True,
            'notifications_sent': notifications_sent,
            'message': f'Đã gửi {notifications_sent} thông báo quyết định'
        })
    except Exception as e:
        log_activity(current_user.id, 'error', f'Notification error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


# Helper functions

def get_candidates_ready_for_step3():
    """Get candidates ready for Step 3 evaluation."""
    candidates = []
    
    # Get candidates who passed Step 1
    step1_passed = AssessmentResult.query.filter_by(
        step=1, status='passed'
    ).all()
    
    for result in step1_passed:
        candidate = Candidate.query.get(result.candidate_id)
        
        # Check if candidate has completed Step 2 with good scores
        step2_evaluations = InterviewEvaluation.query.filter_by(
            candidate_id=candidate.id, status='completed'
        ).all()
        
        if step2_evaluations:
            avg_score = sum(e.overall_score for e in step2_evaluations) / len(step2_evaluations)
            if avg_score >= 7:  # Good Step 2 performance
                candidates.append({
                    'candidate': candidate,
                    'step1_score': result.score,
                    'step2_avg_score': avg_score,
                    'step2_evaluations': step2_evaluations
                })
    
    return candidates


def is_candidate_ready_for_step3(candidate_id):
    """Check if candidate is ready for Step 3."""
    # Check Step 1
    step1_result = AssessmentResult.query.filter_by(
        candidate_id=candidate_id, step=1, status='passed'
    ).first()
    
    if not step1_result:
        return False
    
    # Check Step 2
    step2_evaluations = InterviewEvaluation.query.filter_by(
        candidate_id=candidate_id, status='completed'
    ).all()
    
    if not step2_evaluations:
        return False
    
    avg_score = sum(e.overall_score for e in step2_evaluations) / len(step2_evaluations)
    return avg_score >= 7


def calculate_decision_statistics():
    """Calculate decision statistics."""
    total_decisions = ExecutiveDecision.query.count()
    completed_decisions = ExecutiveDecision.query.filter_by(status='completed').count()
    pending_decisions = ExecutiveDecision.query.filter_by(status='pending').count()
    
    # Get hiring statistics
    hire_decisions = ExecutiveDecision.query.filter_by(final_decision='hire').count()
    reject_decisions = ExecutiveDecision.query.filter_by(final_decision='reject').count()
    review_decisions = ExecutiveDecision.query.filter_by(final_decision='manual_review').count()
    
    return {
        'total': total_decisions,
        'completed': completed_decisions,
        'pending': pending_decisions,
        'hire_rate': (hire_decisions / completed_decisions * 100) if completed_decisions > 0 else 0,
        'reject_rate': (reject_decisions / completed_decisions * 100) if completed_decisions > 0 else 0,
        'review_rate': (review_decisions / completed_decisions * 100) if completed_decisions > 0 else 0
    }


def send_final_decision_notification(decision):
    """Send notification for final decision."""
    try:
        candidate = Candidate.query.get(decision.candidate_id)
        cto = User.query.get(decision.cto_id)
        ceo = User.query.get(decision.ceo_id)
        
        subject = f"Quyết định cuối cùng - {candidate.name}"
        body = f"""
        Xin chào HR Team,
        
        Quyết định cuối cùng cho ứng viên {candidate.name} đã được hoàn thành.
        
        Thông tin quyết định:
        - CTO: {cto.username} - Điểm: {decision.cto_score}/10 - Khuyến nghị: {decision.cto_recommendation}
        - CEO: {ceo.username} - Điểm: {decision.ceo_score}/10 - Khuyến nghị: {decision.ceo_recommendation}
        - Điểm trung bình: {(decision.cto_score + decision.ceo_score) / 2}/10
        - Quyết định cuối: {decision.final_decision}
        
        Trân trọng,
        Mekong Recruitment System
        """
        
        # Send to HR users
        hr_users = User.query.filter_by(role='hr').all()
        for hr_user in hr_users:
            send_email(hr_user.email, subject, body)
        
        return True
    except Exception as e:
        log_activity(current_user.id, 'error', f'Final decision notification error: {str(e)}')
        return False


def send_compensation_approval_notification(decision):
    """Send notification for compensation approval."""
    try:
        candidate = Candidate.query.get(decision.candidate_id)
        
        subject = f"Phê duyệt lương thưởng - {candidate.name}"
        body = f"""
        Xin chào HR Team,
        
        Lương thưởng cho ứng viên {candidate.name} đã được phê duyệt bởi cả CTO và CEO.
        
        Ứng viên này đã sẵn sàng để offer.
        
        Trân trọng,
        Mekong Recruitment System
        """
        
        # Send to HR users
        hr_users = User.query.filter_by(role='hr').all()
        for hr_user in hr_users:
            send_email(hr_user.email, subject, body)
        
        return True
    except Exception as e:
        log_activity(current_user.id, 'error', f'Compensation approval notification error: {str(e)}')
        return False


def send_decision_reminder(decision):
    """Send reminder for pending decision."""
    try:
        candidate = Candidate.query.get(decision.candidate_id)
        
        # Determine which executive needs to make decision
        if not decision.cto_id:
            executive_role = 'CTO'
            executive_email = 'cto@mekong.com'  # Replace with actual CTO email
        elif not decision.ceo_id:
            executive_role = 'CEO'
            executive_email = 'ceo@mekong.com'  # Replace with actual CEO email
        else:
            return False  # Both decisions already made
        
        subject = f"Nhắc nhở quyết định - {candidate.name}"
        body = f"""
        Xin chào {executive_role},
        
        Nhắc nhở: Bạn cần đưa ra quyết định cho ứng viên {candidate.name}.
        
        Thông tin ứng viên:
        - Vị trí: {candidate.position.title}
        - Phòng ban: {candidate.position.department}
        - Điểm Step 1: {decision.candidate.assessment_results[0].score if decision.candidate.assessment_results else 'N/A'}
        
        Vui lòng truy cập hệ thống để đưa ra quyết định.
        
        Trân trọng,
        Mekong Recruitment System
        """
        
        send_email(executive_email, subject, body)
        return True
    except Exception as e:
        log_activity(current_user.id, 'error', f'Decision reminder error: {str(e)}')
        return False 