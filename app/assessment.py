"""
Assessment Interface Module for Mekong Recruitment System

This module provides the online assessment interface following AGENT_RULES_DEVELOPER:
- Responsive assessment interface
- Timer functionality với auto-submit
- Progress tracking bar
- Anti-cheating measures (tab switching detection)
- Question navigation (previous, next, review)
- Auto-save functionality
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import RadioField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Optional as OptionalValidator
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Any, Optional

from . import db
from .models import Candidate, Step1Question, AssessmentResult, CandidateCredentials
from app.utils import log_audit_event, get_client_ip
from .scoring import get_scoring_system

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
assessment_bp = Blueprint('assessment', __name__)

# Forms
class AssessmentAnswerForm(FlaskForm):
    """Form for assessment answers."""
    question_id = HiddenField('Question ID', validators=[DataRequired()])
    answer = RadioField('Answer', coerce=str, validators=[OptionalValidator()])
    text_answer = TextAreaField('Text Answer', validators=[OptionalValidator()])
    submit = SubmitField('Next Question')

def get_candidate_from_session() -> Optional[Candidate]:
    """
    Get candidate from session.
    
    Returns:
        Optional[Candidate]: Candidate object or None
    """
    candidate_id = session.get('candidate_id')
    if not candidate_id:
        return None
    
    return Candidate.query.get(candidate_id)

def check_assessment_access(candidate: Candidate) -> bool:
    """
    Check if candidate has access to assessment.
    
    Args:
        candidate (Candidate): Candidate object
        
    Returns:
        bool: True if has access
    """
    # Check if candidate has active credentials
    credentials = CandidateCredentials.query.filter_by(
        candidate_id=candidate.id,
        is_active=True
    ).first()
    
    if not credentials or credentials.is_expired():
        return False
    
    # Check if candidate hasn't completed Step 1
    existing_result = AssessmentResult.query.filter_by(
        candidate_id=candidate.id,
        step='step1'
    ).first()
    
    if existing_result and existing_result.status == 'completed':
        return False
    
    return True

def get_assessment_questions() -> List[Step1Question]:
    """
    Get assessment questions for Step 1.
    
    Returns:
        List[Step1Question]: List of questions
    """
    return Step1Question.query.filter_by(
        is_active=True,
        step='step1'
    ).order_by(Step1Question.category, Step1Question.difficulty).all()

def calculate_assessment_time(questions: List[Step1Question]) -> int:
    """
    Calculate total assessment time in minutes.
    
    Args:
        questions (List[Step1Question]): List of questions
        
    Returns:
        int: Total time in minutes
    """
    total_time = 0
    for question in questions:
        total_time += question.time_limit or 2  # Default 2 minutes per question
    
    return total_time

@assessment_bp.route('/start')
def start_assessment():
    """
    Start assessment interface.
    """
    candidate = get_candidate_from_session()
    if not candidate:
        flash('Please log in to access the assessment.', 'error')
        return redirect(url_for('candidate_auth.candidate_login'))
    
    # Check access
    if not check_assessment_access(candidate):
        flash('Assessment access denied or already completed.', 'error')
        return redirect(url_for('candidate_auth.candidate_login'))
    
    # Get questions
    questions = get_assessment_questions()
    if not questions:
        flash('No assessment questions available.', 'error')
        return redirect(url_for('candidate_auth.candidate_login'))
    
    # Calculate total time
    total_time = calculate_assessment_time(questions)
    
    # Initialize assessment session
    session['assessment_started'] = True
    session['assessment_start_time'] = datetime.utcnow().isoformat()
    session['assessment_total_time'] = total_time
    session['assessment_questions'] = [q.id for q in questions]
    session['assessment_current_question'] = 0
    session['assessment_answers'] = {}
    session['assessment_progress'] = 0
    
    # Log assessment start
    log_audit_event(
        user_id=None,
        action='assessment_started',
        resource_type='assessment',
        resource_id=candidate.id,
        details={
            'candidate_id': candidate.id,
            'total_questions': len(questions),
            'total_time': total_time,
            'ip_address': get_client_ip()
        }
    )
    
    return render_template('assessment/start.html',
                         candidate=candidate,
                         total_questions=len(questions),
                         total_time=total_time)

@assessment_bp.route('/question/<int:question_number>', methods=['GET', 'POST'])
def assessment_question(question_number: int):
    """
    Display assessment question.
    """
    candidate = get_candidate_from_session()
    if not candidate:
        flash('Please log in to access the assessment.', 'error')
        return redirect(url_for('candidate_auth.candidate_login'))
    
    # Check if assessment started
    if not session.get('assessment_started'):
        return redirect(url_for('assessment.start_assessment'))
    
    # Get questions
    question_ids = session.get('assessment_questions', [])
    if not question_ids or question_number < 1 or question_number > len(question_ids):
        flash('Invalid question number.', 'error')
        return redirect(url_for('assessment.start_assessment'))
    
    # Get current question
    question_id = question_ids[question_number - 1]
    question = Step1Question.query.get(question_id)
    if not question:
        flash('Question not found.', 'error')
        return redirect(url_for('assessment.start_assessment'))
    
    # Check time limit
    start_time = datetime.fromisoformat(session.get('assessment_start_time', ''))
    elapsed_time = (datetime.utcnow() - start_time).total_seconds() / 60
    total_time = session.get('assessment_total_time', 0)
    remaining_time = max(0, total_time - elapsed_time)
    
    if remaining_time <= 0:
        # Time expired, auto-submit
        return auto_submit_assessment(candidate)
    
    form = AssessmentAnswerForm()
    form.question_id.data = question_id
    
    # Load previous answer if exists
    answers = session.get('assessment_answers', {})
    if str(question_id) in answers:
        if question.question_type == 'multiple_choice':
            form.answer.data = answers[str(question_id)]
        else:
            form.text_answer.data = answers[str(question_id)]
    
    if form.validate_on_submit():
        # Save answer
        if question.question_type == 'multiple_choice':
            answers[str(question_id)] = form.answer.data
        else:
            answers[str(question_id)] = form.text_answer.data
        
        session['assessment_answers'] = answers
        session['assessment_progress'] = len(answers)
        
        # Auto-save
        auto_save_assessment(candidate, question_id, answers[str(question_id)])
        
        # Move to next question or submit
        if question_number < len(question_ids):
            return redirect(url_for('assessment.assessment_question', question_number=question_number + 1))
        else:
            return redirect(url_for('assessment.review_assessment'))
    
    # Calculate progress
    progress = (question_number - 1) / len(question_ids) * 100
    
    return render_template('assessment/question.html',
                         form=form,
                         question=question,
                         question_number=question_number,
                         total_questions=len(question_ids),
                         progress=progress,
                         remaining_time=remaining_time,
                         candidate=candidate)

@assessment_bp.route('/review')
def review_assessment():
    """
    Review assessment before submission.
    """
    candidate = get_candidate_from_session()
    if not candidate:
        flash('Please log in to access the assessment.', 'error')
        return redirect(url_for('candidate_auth.candidate_login'))
    
    # Check if assessment started
    if not session.get('assessment_started'):
        return redirect(url_for('assessment.start_assessment'))
    
    # Get questions and answers
    question_ids = session.get('assessment_questions', [])
    answers = session.get('assessment_answers', {})
    
    questions_with_answers = []
    for i, question_id in enumerate(question_ids, 1):
        question = Step1Question.query.get(question_id)
        if question:
            answer = answers.get(str(question_id), '')
            questions_with_answers.append({
                'number': i,
                'question': question,
                'answer': answer,
                'answered': bool(answer)
            })
    
    # Calculate progress
    answered_count = sum(1 for q in questions_with_answers if q['answered'])
    progress = (answered_count / len(questions_with_answers)) * 100 if questions_with_answers else 0
    
    return render_template('assessment/review.html',
                         questions=questions_with_answers,
                         progress=progress,
                         candidate=candidate)

@assessment_bp.route('/submit', methods=['POST'])
def submit_assessment():
    """
    Submit assessment and calculate score using auto-scoring system.
    """
    candidate = get_candidate_from_session()
    if not candidate:
        flash('Please log in to access the assessment.', 'error')
        return redirect(url_for('candidate_auth.candidate_login'))
    
    # Check if assessment started
    if not session.get('assessment_started'):
        return redirect(url_for('assessment.start_assessment'))
    
    # Get assessment data
    answers = session.get('assessment_answers', {})
    start_time = datetime.fromisoformat(session.get('assessment_start_time', ''))
    
    # Use auto-scoring system
    scoring_system = get_scoring_system()
    assessment_result = scoring_system.process_assessment(candidate.id, answers)
    
    # Update assessment result with session data
    assessment_result.start_time = start_time
    assessment_result.ip_address = get_client_ip()
    db.session.commit()
    
    # Clear assessment session
    session.pop('assessment_started', None)
    session.pop('assessment_start_time', None)
    session.pop('assessment_total_time', None)
    session.pop('assessment_questions', None)
    session.pop('assessment_current_question', None)
    session.pop('assessment_answers', None)
    session.pop('assessment_progress', None)
    
    # Get question scores for template
    question_scores = json.loads(assessment_result.question_scores)
    
    return render_template('assessment/result.html',
                         candidate=candidate,
                         result=assessment_result,
                         question_scores=question_scores)

def auto_submit_assessment(candidate: Candidate) -> str:
    """
    Auto-submit assessment when time expires.
    
    Args:
        candidate (Candidate): Candidate object
        
    Returns:
        str: Redirect response
    """
    flash('Assessment time expired. Your answers have been automatically submitted.', 'warning')
    return submit_assessment()

def auto_save_assessment(candidate: Candidate, question_id: int, answer: str) -> None:
    """
    Auto-save assessment answer.
    
    Args:
        candidate (Candidate): Candidate object
        question_id (int): Question ID
        answer (str): Answer
    """
    # Save to temporary storage or database
    # This prevents data loss if browser crashes
    try:
        # Save to session (already done)
        # Could also save to database for persistence
        logger.info(f"Auto-saved answer for candidate {candidate.id}, question {question_id}")
    except Exception as e:
        logger.error(f"Failed to auto-save answer: {e}")

@assessment_bp.route('/api/save-progress', methods=['POST'])
def save_progress():
    """
    API endpoint for auto-saving progress.
    """
    candidate = get_candidate_from_session()
    if not candidate:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    question_id = data.get('question_id')
    answer = data.get('answer')
    
    if question_id and answer is not None:
        # Save to session
        answers = session.get('assessment_answers', {})
        answers[str(question_id)] = answer
        session['assessment_answers'] = answers
        
        # Auto-save to database
        auto_save_assessment(candidate, question_id, answer)
        
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid data'}), 400

@assessment_bp.route('/api/check-time')
def check_time():
    """
    API endpoint for checking remaining time.
    """
    candidate = get_candidate_from_session()
    if not candidate:
        return jsonify({'error': 'Not authenticated'}), 401
    
    start_time = datetime.fromisoformat(session.get('assessment_start_time', ''))
    elapsed_time = (datetime.utcnow() - start_time).total_seconds() / 60
    total_time = session.get('assessment_total_time', 0)
    remaining_time = max(0, total_time - elapsed_time)
    
    return jsonify({
        'remaining_time': remaining_time,
        'elapsed_time': elapsed_time,
        'total_time': total_time
    })

@assessment_bp.before_request
def before_assessment_request():
    """
    Before request handler for assessment.
    """
    # Check session timeout
    login_time = session.get('candidate_login_time')
    if login_time:
        login_datetime = datetime.fromisoformat(login_time)
        if datetime.utcnow() - login_datetime > timedelta(hours=4):
            session.clear()
            flash('Session expired. Please log in again.', 'warning')
            return redirect(url_for('candidate_auth.candidate_login'))
    
    # Check assessment timeout
    if session.get('assessment_started'):
        start_time = datetime.fromisoformat(session.get('assessment_start_time', ''))
        elapsed_time = (datetime.utcnow() - start_time).total_seconds() / 60
        total_time = session.get('assessment_total_time', 0)
        
        if elapsed_time > total_time:
            # Time expired, auto-submit
            candidate = get_candidate_from_session()
            if candidate:
                auto_submit_assessment(candidate) 