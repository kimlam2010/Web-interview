"""
Interview Setup Interface - Task 5.1
Manages Step 2 technical interview setup and scheduling
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.exceptions import Forbidden
from datetime import datetime, timedelta
import json
import uuid

from .models import db, Candidate, Position, Step1Question, Step2Question, Step3Question, InterviewEvaluation, AssessmentResult, User
from .decorators import hr_required, interviewer_required
from app.utils import log_activity, send_email

interview_bp = Blueprint('interview', __name__)


@interview_bp.route('/setup')
@login_required
@hr_required
def interview_setup():
    """Main interview setup interface for HR."""
    try:
        # Get candidates ready for Step 2 (passed Step 1)
        candidates = Candidate.query.join(AssessmentResult).filter(
            AssessmentResult.step == 1,
            AssessmentResult.status.in_(['passed', 'manual_review'])
        ).all()
        
        # Get available positions
        positions = Position.query.all()
        
        # Get Step 2 questions by category
        questions = Step2Question.query.all()
        questions_by_category = {}
        for q in questions:
            if q.category not in questions_by_category:
                questions_by_category[q.category] = []
            questions_by_category[q.category].append(q)
        
        return render_template('interview/setup.html',
                             candidates=candidates,
                             positions=positions,
                             questions_by_category=questions_by_category)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Interview setup error: {str(e)}')
        flash('Có lỗi xảy ra khi tải giao diện thiết lập phỏng vấn.', 'error')
        return redirect(url_for('main.dashboard'))


@interview_bp.route('/setup/<int:candidate_id>')
@login_required
@hr_required
def candidate_interview_setup(candidate_id):
    """Setup interview for specific candidate."""
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        
        # Check if candidate passed Step 1
        step1_result = AssessmentResult.query.filter_by(
            candidate_id=candidate_id, step=1
        ).first()
        
        if not step1_result or step1_result.status not in ['passed', 'manual_review']:
            flash('Ứng viên chưa hoàn thành hoặc không đạt Step 1.', 'warning')
            return redirect(url_for('interview.interview_setup'))
        
        # Get position details
        position = Position.query.get(candidate.position_id)
        
        # Get Step 2 questions filtered by position
        questions = Step2Question.query.all()
        
        # Filter questions by position level
        filtered_questions = filter_questions_by_position(questions, position)
        
        return render_template('interview/candidate_setup.html',
                             candidate=candidate,
                             position=position,
                             step1_result=step1_result,
                             questions=filtered_questions)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Candidate interview setup error: {str(e)}')
        flash('Có lỗi xảy ra khi thiết lập phỏng vấn cho ứng viên.', 'error')
        return redirect(url_for('interview.interview_setup'))


@interview_bp.route('/setup/<int:candidate_id>/questions', methods=['GET', 'POST'])
@login_required
@hr_required
def select_interview_questions(candidate_id):
    """Select questions for candidate interview."""
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        position = Position.query.get(candidate.position_id)
        
        if request.method == 'POST':
            selected_questions = request.form.getlist('questions')
            interview_duration = int(request.form.get('duration', 60))
            interview_date = datetime.strptime(request.form.get('interview_date'), '%Y-%m-%d')
            interview_time = request.form.get('interview_time')
            
            if len(selected_questions) < 3:
                flash('Vui lòng chọn ít nhất 3 câu hỏi cho phỏng vấn.', 'warning')
                return redirect(url_for('interview.select_interview_questions', candidate_id=candidate_id))
            
            # Create interview evaluation record
            evaluation = InterviewEvaluation(
                candidate_id=candidate_id,
                interviewer_id=current_user.id,
                questions=json.dumps(selected_questions),
                scheduled_date=interview_date,
                scheduled_time=interview_time,
                duration=interview_duration,
                status='scheduled'
            )
            
            db.session.add(evaluation)
            db.session.commit()
            
            # Generate interview link
            interview_link = generate_interview_link(evaluation.id)
            
            log_activity(current_user.id, 'interview_scheduled', 
                        f'Scheduled interview for candidate {candidate_id}')
            
            flash('Phỏng vấn đã được thiết lập thành công!', 'success')
            return redirect(url_for('interview.interview_setup'))
        
        # Get questions by category
        questions = Step2Question.query.all()
        questions_by_category = {}
        for q in questions:
            if q.category not in questions_by_category:
                questions_by_category[q.category] = []
            questions_by_category[q.category].append(q)
        
        return render_template('interview/select_questions.html',
                             candidate=candidate,
                             position=position,
                             questions_by_category=questions_by_category)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Question selection error: {str(e)}')
        flash('Có lỗi xảy ra khi chọn câu hỏi phỏng vấn.', 'error')
        return redirect(url_for('interview.interview_setup'))


@interview_bp.route('/assign-interviewer/<int:candidate_id>', methods=['POST'])
@login_required
@hr_required
def assign_interviewer(candidate_id):
    """Assign interviewer to candidate."""
    try:
        interviewer_id = request.form.get('interviewer_id')
        interview_date = datetime.strptime(request.form.get('interview_date'), '%Y-%m-%d')
        interview_time = request.form.get('interview_time')
        
        # Create or update interview evaluation
        evaluation = InterviewEvaluation.query.filter_by(
            candidate_id=candidate_id, status='scheduled'
        ).first()
        
        if not evaluation:
            evaluation = InterviewEvaluation(
                candidate_id=candidate_id,
                interviewer_id=interviewer_id,
                scheduled_date=interview_date,
                scheduled_time=interview_time,
                status='scheduled'
            )
            db.session.add(evaluation)
        else:
            evaluation.interviewer_id = interviewer_id
            evaluation.scheduled_date = interview_date
            evaluation.scheduled_time = interview_time
        
        db.session.commit()
        
        log_activity(current_user.id, 'interviewer_assigned', 
                    f'Assigned interviewer {interviewer_id} to candidate {candidate_id}')
        
        return jsonify({'success': True, 'message': 'Interviewer assigned successfully'})
    except Exception as e:
        log_activity(current_user.id, 'error', f'Interviewer assignment error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@interview_bp.route('/generate-link/<int:evaluation_id>')
@login_required
@hr_required
def generate_interview_link(evaluation_id):
    """Generate unique interview link."""
    try:
        evaluation = InterviewEvaluation.query.get_or_404(evaluation_id)
        
        # Generate unique link ID
        link_id = str(uuid.uuid4())[:16]
        
        # Update evaluation with link
        evaluation.interview_link = link_id
        evaluation.link_expires_at = datetime.utcnow() + timedelta(days=7)
        
        db.session.commit()
        
        # Send email to interviewer
        send_interview_notification(evaluation)
        
        log_activity(current_user.id, 'link_generated', 
                    f'Generated interview link for evaluation {evaluation_id}')
        
        return jsonify({
            'success': True,
            'link': url_for('interview.candidate_interview', link_id=link_id, _external=True)
        })
    except Exception as e:
        log_activity(current_user.id, 'error', f'Link generation error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@interview_bp.route('/track-status')
@login_required
@hr_required
def track_interview_status():
    """Track interview status for all candidates."""
    try:
        # Get all scheduled interviews
        scheduled_interviews = InterviewEvaluation.query.filter_by(
            status='scheduled'
        ).join(Candidate).all()
        
        # Get completed interviews
        completed_interviews = InterviewEvaluation.query.filter_by(
            status='completed'
        ).join(Candidate).all()
        
        # Get pending interviews (passed Step 1, no Step 2 scheduled)
        step1_passed = AssessmentResult.query.filter_by(
            step=1, status='passed'
        ).all()
        
        pending_candidates = []
        for result in step1_passed:
            has_interview = InterviewEvaluation.query.filter_by(
                candidate_id=result.candidate_id
            ).first()
            if not has_interview:
                candidate = Candidate.query.get(result.candidate_id)
                pending_candidates.append(candidate)
        
        return render_template('interview/track_status.html',
                             scheduled_interviews=scheduled_interviews,
                             completed_interviews=completed_interviews,
                             pending_candidates=pending_candidates)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Status tracking error: {str(e)}')
        flash('Có lỗi xảy ra khi theo dõi trạng thái phỏng vấn.', 'error')
        return redirect(url_for('main.dashboard'))


@interview_bp.route('/reminders')
@login_required
@hr_required
def send_interview_reminders():
    """Send interview reminders."""
    try:
        # Get interviews scheduled for tomorrow
        tomorrow = datetime.utcnow() + timedelta(days=1)
        tomorrow_interviews = InterviewEvaluation.query.filter(
            InterviewEvaluation.scheduled_date == tomorrow.date(),
            InterviewEvaluation.status == 'scheduled'
        ).all()
        
        reminders_sent = 0
        for interview in tomorrow_interviews:
            if send_interview_reminder(interview):
                reminders_sent += 1
        
        log_activity(current_user.id, 'reminders_sent', 
                    f'Sent {reminders_sent} interview reminders')
        
        return jsonify({
            'success': True,
            'reminders_sent': reminders_sent,
            'message': f'Đã gửi {reminders_sent} nhắc nhở phỏng vấn'
        })
    except Exception as e:
        log_activity(current_user.id, 'error', f'Reminder error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


# Task 5.2: Interview Evaluation System

@interview_bp.route('/evaluation/<int:evaluation_id>')
@login_required
@interviewer_required
def interview_evaluation(evaluation_id):
    """Interview evaluation interface for interviewer."""
    try:
        evaluation = InterviewEvaluation.query.get_or_404(evaluation_id)
        
        # Check if current user is the assigned interviewer
        if evaluation.interviewer_id != current_user.id:
            flash('Bạn không được phép đánh giá phỏng vấn này.', 'error')
            return redirect(url_for('interview.interviewer_dashboard'))
        
        candidate = Candidate.query.get(evaluation.candidate_id)
        position = Position.query.get(candidate.position_id)
        
        # Get selected questions
        selected_question_ids = json.loads(evaluation.questions) if evaluation.questions else []
        selected_questions = Step2Question.query.filter(Step2Question.id.in_(selected_question_ids)).all()
        
        return render_template('interview/evaluation.html',
                             evaluation=evaluation,
                             candidate=candidate,
                             position=position,
                             questions=selected_questions)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Evaluation interface error: {str(e)}')
        flash('Có lỗi xảy ra khi tải giao diện đánh giá.', 'error')
        return redirect(url_for('interview.interviewer_dashboard'))


@interview_bp.route('/evaluation/<int:evaluation_id>/submit', methods=['POST'])
@login_required
@interviewer_required
def submit_evaluation(evaluation_id):
    """Submit interview evaluation."""
    try:
        evaluation = InterviewEvaluation.query.get_or_404(evaluation_id)
        
        if evaluation.interviewer_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        # Get evaluation data
        scores = {}
        notes = {}
        
        for key, value in request.form.items():
            if key.startswith('score_'):
                question_id = key.replace('score_', '')
                scores[question_id] = int(value)
            elif key.startswith('notes_'):
                question_id = key.replace('notes_', '')
                notes[question_id] = value
        
        # Calculate overall score
        if scores:
            overall_score = sum(scores.values()) / len(scores)
        else:
            overall_score = 0
        
        # Determine recommendation
        if overall_score >= 7:
            recommendation = 'pass'
        elif overall_score >= 5:
            recommendation = 'manual_review'
        else:
            recommendation = 'fail'
        
        # Update evaluation
        evaluation.overall_score = overall_score
        evaluation.question_scores = json.dumps(scores)
        evaluation.notes = json.dumps(notes)
        evaluation.recommendation = recommendation
        evaluation.status = 'completed'
        evaluation.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log activity
        log_activity(current_user.id, 'evaluation_submitted', 
                    f'Submitted evaluation for candidate {evaluation.candidate_id}')
        
        # Send notification to HR
        send_evaluation_notification(evaluation)
        
        return jsonify({
            'success': True,
            'message': 'Đánh giá đã được gửi thành công!',
            'overall_score': overall_score,
            'recommendation': recommendation
        })
    except Exception as e:
        log_activity(current_user.id, 'error', f'Evaluation submission error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@interview_bp.route('/interviewer/dashboard')
@login_required
@interviewer_required
def interviewer_dashboard():
    """Interviewer dashboard."""
    try:
        # Get assigned interviews
        assigned_interviews = InterviewEvaluation.query.filter_by(
            interviewer_id=current_user.id
        ).join(Candidate).all()
        
        # Get completed evaluations
        completed_evaluations = InterviewEvaluation.query.filter_by(
            interviewer_id=current_user.id,
            status='completed'
        ).join(Candidate).all()
        
        return render_template('interview/interviewer_dashboard.html',
                             assigned_interviews=assigned_interviews,
                             completed_evaluations=completed_evaluations)
    except Exception as e:
        log_activity(current_user.id, 'error', f'Interviewer dashboard error: {str(e)}')
        flash('Có lỗi xảy ra khi tải dashboard.', 'error')
        return redirect(url_for('main.dashboard'))


@interview_bp.route('/evaluation/<int:evaluation_id>/view')
@login_required
@hr_required
def view_evaluation(evaluation_id):
    """View interview evaluation (HR only)."""
    try:
        evaluation = InterviewEvaluation.query.get_or_404(evaluation_id)
        candidate = Candidate.query.get(evaluation.candidate_id)
        interviewer = User.query.get(evaluation.interviewer_id)
        
        # Parse scores and notes
        scores = json.loads(evaluation.question_scores) if evaluation.question_scores else {}
        notes = json.loads(evaluation.notes) if evaluation.notes else {}
        
        # Get questions
        selected_question_ids = json.loads(evaluation.questions) if evaluation.questions else []
        questions = Step2Question.query.filter(Step2Question.id.in_(selected_question_ids)).all()
        
        return render_template('interview/view_evaluation.html',
                             evaluation=evaluation,
                             candidate=candidate,
                             interviewer=interviewer,
                             scores=scores,
                             notes=notes,
                             questions=questions)
    except Exception as e:
        log_activity(current_user.id, 'error', f'View evaluation error: {str(e)}')
        flash('Có lỗi xảy ra khi xem đánh giá.', 'error')
        return redirect(url_for('interview.interview_setup'))


# Helper functions

def filter_questions_by_position(questions, position):
    """Filter questions based on position level and requirements."""
    filtered = []
    
    for question in questions:
        # Basic filtering logic - can be enhanced
        if position.level in ['Senior', 'Lead']:
            # Include all questions for senior positions
            filtered.append(question)
        elif position.level == 'Mid':
            # Exclude very advanced questions
            if 'advanced' not in question.content.lower():
                filtered.append(question)
        else:  # Junior
            # Only include basic questions
            if 'basic' in question.content.lower() or 'fundamental' in question.content.lower():
                filtered.append(question)
    
    return filtered


def generate_interview_link(evaluation_id):
    """Generate unique interview link."""
    link_id = str(uuid.uuid4())[:16]
    return f"/interview/{link_id}"


def send_interview_notification(evaluation):
    """Send interview notification to interviewer."""
    try:
        candidate = Candidate.query.get(evaluation.candidate_id)
        interviewer = User.query.get(evaluation.interviewer_id)
        
        subject = f"Phỏng vấn mới được giao - {candidate.name}"
        body = f"""
        Xin chào {interviewer.username},
        
        Bạn đã được giao phỏng vấn ứng viên {candidate.name} cho vị trí {candidate.position.title}.
        
        Thông tin phỏng vấn:
        - Ngày: {evaluation.scheduled_date.strftime('%d/%m/%Y')}
        - Giờ: {evaluation.scheduled_time}
        - Thời gian: {evaluation.duration} phút
        
        Link phỏng vấn: {url_for('interview.candidate_interview', link_id=evaluation.interview_link, _external=True)}
        
        Trân trọng,
        Mekong Recruitment System
        """
        
        send_email(interviewer.email, subject, body)
        return True
    except Exception as e:
        log_activity(current_user.id, 'error', f'Notification error: {str(e)}')
        return False


def send_interview_reminder(interview):
    """Send interview reminder."""
    try:
        candidate = Candidate.query.get(interview.candidate_id)
        interviewer = User.query.get(interview.interviewer_id)
        
        subject = f"Nhắc nhở phỏng vấn - {candidate.name}"
        body = f"""
        Xin chào {interviewer.username},
        
        Nhắc nhở: Bạn có lịch phỏng vấn ứng viên {candidate.name} vào ngày mai.
        
        Thông tin phỏng vấn:
        - Ngày: {interview.scheduled_date.strftime('%d/%m/%Y')}
        - Giờ: {interview.scheduled_time}
        - Thời gian: {interview.duration} phút
        
        Link phỏng vấn: {url_for('interview.candidate_interview', link_id=interview.interview_link, _external=True)}
        
        Trân trọng,
        Mekong Recruitment System
        """
        
        send_email(interviewer.email, subject, body)
        return True
    except Exception as e:
        log_activity(current_user.id, 'error', f'Reminder error: {str(e)}')
        return False


def send_evaluation_notification(evaluation):
    """Send evaluation notification to HR."""
    try:
        candidate = Candidate.query.get(evaluation.candidate_id)
        interviewer = User.query.get(evaluation.interviewer_id)
        
        subject = f"Đánh giá phỏng vấn hoàn thành - {candidate.name}"
        body = f"""
        Xin chào HR Team,
        
        Đánh giá phỏng vấn cho ứng viên {candidate.name} đã được hoàn thành.
        
        Thông tin đánh giá:
        - Interviewer: {interviewer.username}
        - Điểm tổng: {evaluation.overall_score}/10
        - Khuyến nghị: {evaluation.recommendation}
        - Ngày hoàn thành: {evaluation.completed_at.strftime('%d/%m/%Y %H:%M')}
        
        Trân trọng,
        Mekong Recruitment System
        """
        
        # Send to HR users
        hr_users = User.query.filter_by(role='hr').all()
        for hr_user in hr_users:
            send_email(hr_user.email, subject, body)
        
        return True
    except Exception as e:
        log_activity(current_user.id, 'error', f'Evaluation notification error: {str(e)}')
        return False 