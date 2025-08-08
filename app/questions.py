"""
Question Bank Management Module for Mekong Recruitment System

This module provides comprehensive question management following AGENT_RULES_DEVELOPER:
- Database models cho Step 1, 2, 3 questions
- Question import từ JSON files
- Question editor interface với step-specific forms
- Question duplication functionality
- Bulk operations (activate, deactivate, delete)
- Question statistics tracking
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
import json
import os
from datetime import datetime
from typing import List, Dict, Any

from . import db
from .models import Step1Question, Step2Question, Step3Question, Position
from .decorators import admin_required, hr_required, audit_action
from app.utils import log_audit_event, get_client_ip

# Create blueprint
questions_bp = Blueprint('questions', __name__)

# Forms
class Step1QuestionForm(FlaskForm):
    """Form for Step 1 questions (IQ + Technical)."""
    question_text = TextAreaField('Question Text', validators=[DataRequired(), Length(min=10)])
    question_type = SelectField('Question Type', choices=[
        ('iq', 'IQ Question'),
        ('technical', 'Technical Question')
    ], validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('logical', 'Logical Reasoning'),
        ('spatial', 'Spatial Reasoning'),
        ('numerical', 'Numerical Reasoning'),
        ('verbal', 'Verbal Reasoning'),
        ('programming', 'Programming'),
        ('databases', 'Databases'),
        ('algorithms', 'Algorithms'),
        ('web_development', 'Web Development'),
        ('mobile_development', 'Mobile Development'),
        ('devops', 'DevOps'),
        ('ai_ml', 'AI/ML')
    ], validators=[DataRequired()])
    difficulty = SelectField('Difficulty', choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], validators=[DataRequired()])
    options = TextAreaField('Options (JSON)', validators=[Optional()])
    correct_answer = StringField('Correct Answer', validators=[DataRequired(), Length(max=10)])
    explanation = TextAreaField('Explanation', validators=[Optional()])
    points = IntegerField('Points', validators=[NumberRange(min=1, max=10)], default=1)
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Question')

class Step2QuestionForm(FlaskForm):
    """Form for Step 2 questions (Technical Interview)."""
    title = StringField('Question Title', validators=[DataRequired(), Length(min=5, max=200)])
    content = TextAreaField('Question Content', validators=[DataRequired(), Length(min=20)])
    category = SelectField('Category', choices=[
        ('programming', 'Programming'),
        ('databases', 'Databases'),
        ('algorithms', 'Algorithms'),
        ('web_development', 'Web Development'),
        ('mobile_development', 'Mobile Development'),
        ('devops', 'DevOps'),
        ('ai_ml', 'AI/ML'),
        ('system_design', 'System Design'),
        ('problem_solving', 'Problem Solving')
    ], validators=[DataRequired()])
    difficulty = SelectField('Difficulty', choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], validators=[DataRequired()])
    time_minutes = IntegerField('Time (minutes)', validators=[NumberRange(min=5, max=60)], default=15)
    evaluation_criteria = TextAreaField('Evaluation Criteria (JSON)', validators=[Optional()])
    related_technologies = TextAreaField('Related Technologies (JSON)', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Question')

class Step3QuestionForm(FlaskForm):
    """Form for Step 3 questions (Executive Interview)."""
    title = StringField('Question Title', validators=[DataRequired(), Length(min=5, max=200)])
    content = TextAreaField('Question Content', validators=[DataRequired(), Length(min=20)])
    question_type = SelectField('Question Type', choices=[
        ('cto', 'CTO Question'),
        ('ceo', 'CEO Question')
    ], validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('leadership', 'Leadership'),
        ('strategy', 'Strategy'),
        ('management', 'Management'),
        ('technical_vision', 'Technical Vision'),
        ('business_acumen', 'Business Acumen'),
        ('culture_fit', 'Culture Fit')
    ], validators=[DataRequired()])
    time_minutes = IntegerField('Time (minutes)', validators=[NumberRange(min=3, max=15)], default=5)
    evaluation_criteria = TextAreaField('Evaluation Criteria (JSON)', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Question')

@questions_bp.route('/questions')
@login_required
@hr_required
@audit_action('view_question_bank')
def question_bank():
    """
    Question bank management page.
    """
    step = request.args.get('step', 'step1')
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')
    is_active = request.args.get('is_active', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get questions based on step
    if step == 'step1':
        query = Step1Question.query
        if category:
            query = query.filter(Step1Question.category == category)
        if difficulty:
            query = query.filter(Step1Question.difficulty == difficulty)
        if is_active:
            query = query.filter(Step1Question.is_active == (is_active == 'true'))
        
        questions = query.order_by(Step1Question.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        question_type = 'Step 1 (IQ + Technical)'
        
    elif step == 'step2':
        query = Step2Question.query
        if category:
            query = query.filter(Step2Question.category == category)
        if difficulty:
            query = query.filter(Step2Question.difficulty == difficulty)
        if is_active:
            query = query.filter(Step2Question.is_active == (is_active == 'true'))
        
        questions = query.order_by(Step2Question.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        question_type = 'Step 2 (Technical Interview)'
        
    elif step == 'step3':
        query = Step3Question.query
        if category:
            query = query.filter(Step3Question.category == category)
        if difficulty:
            query = query.filter(Step3Question.difficulty == difficulty)
        if is_active:
            query = query.filter(Step3Question.is_active == (is_active == 'true'))
        
        questions = query.order_by(Step3Question.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        question_type = 'Step 3 (Executive Interview)'
    
    return render_template('questions/bank.html',
                         questions=questions,
                         step=step,
                         question_type=question_type,
                         category=category,
                         difficulty=difficulty,
                         is_active=is_active)

@questions_bp.route('/questions/step1/add', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('add_step1_question')
def add_step1_question():
    """
    Add new Step 1 question.
    """
    form = Step1QuestionForm()
    
    if form.validate_on_submit():
        # Validate options JSON
        options = None
        if form.options.data:
            try:
                options = json.loads(form.options.data)
                if not isinstance(options, list):
                    raise ValueError("Options must be a JSON array")
            except (json.JSONDecodeError, ValueError) as e:
                flash(f'Invalid options JSON: {str(e)}', 'error')
                return render_template('questions/add_step1.html', form=form)
        
        question = Step1Question(
            question_text=form.question_text.data,
            question_type=form.question_type.data,
            category=form.category.data,
            difficulty=form.difficulty.data,
            options=json.dumps(options) if options else None,
            correct_answer=form.correct_answer.data,
            explanation=form.explanation.data,
            points=form.points.data,
            is_active=form.is_active.data
        )
        
        db.session.add(question)
        db.session.commit()
        
        flash('Step 1 question added successfully.', 'success')
        return redirect(url_for('questions.question_bank', step='step1'))
    
    return render_template('questions/add_step1.html', form=form)

@questions_bp.route('/questions/step2/add', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('add_step2_question')
def add_step2_question():
    """
    Add new Step 2 question.
    """
    form = Step2QuestionForm()
    
    if form.validate_on_submit():
        # Validate evaluation criteria JSON
        evaluation_criteria = None
        if form.evaluation_criteria.data:
            try:
                evaluation_criteria = json.loads(form.evaluation_criteria.data)
                if not isinstance(evaluation_criteria, list):
                    raise ValueError("Evaluation criteria must be a JSON array")
            except (json.JSONDecodeError, ValueError) as e:
                flash(f'Invalid evaluation criteria JSON: {str(e)}', 'error')
                return render_template('questions/add_step2.html', form=form)
        
        # Validate related technologies JSON
        related_technologies = None
        if form.related_technologies.data:
            try:
                related_technologies = json.loads(form.related_technologies.data)
                if not isinstance(related_technologies, list):
                    raise ValueError("Related technologies must be a JSON array")
            except (json.JSONDecodeError, ValueError) as e:
                flash(f'Invalid related technologies JSON: {str(e)}', 'error')
                return render_template('questions/add_step2.html', form=form)
        
        question = Step2Question(
            title=form.title.data,
            content=form.content.data,
            category=form.category.data,
            difficulty=form.difficulty.data,
            time_minutes=form.time_minutes.data,
            evaluation_criteria=json.dumps(evaluation_criteria) if evaluation_criteria else None,
            related_technologies=json.dumps(related_technologies) if related_technologies else None,
            is_active=form.is_active.data
        )
        
        db.session.add(question)
        db.session.commit()
        
        flash('Step 2 question added successfully.', 'success')
        return redirect(url_for('questions.question_bank', step='step2'))
    
    return render_template('questions/add_step2.html', form=form)

@questions_bp.route('/questions/step3/add', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('add_step3_question')
def add_step3_question():
    """
    Add new Step 3 question.
    """
    form = Step3QuestionForm()
    
    if form.validate_on_submit():
        # Validate evaluation criteria JSON
        evaluation_criteria = None
        if form.evaluation_criteria.data:
            try:
                evaluation_criteria = json.loads(form.evaluation_criteria.data)
                if not isinstance(evaluation_criteria, list):
                    raise ValueError("Evaluation criteria must be a JSON array")
            except (json.JSONDecodeError, ValueError) as e:
                flash(f'Invalid evaluation criteria JSON: {str(e)}', 'error')
                return render_template('questions/add_step3.html', form=form)
        
        question = Step3Question(
            title=form.title.data,
            content=form.content.data,
            question_type=form.question_type.data,
            category=form.category.data,
            time_minutes=form.time_minutes.data,
            evaluation_criteria=json.dumps(evaluation_criteria) if evaluation_criteria else None,
            is_active=form.is_active.data
        )
        
        db.session.add(question)
        db.session.commit()
        
        flash('Step 3 question added successfully.', 'success')
        return redirect(url_for('questions.question_bank', step='step3'))
    
    return render_template('questions/add_step3.html', form=form)

@questions_bp.route('/questions/import', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('import_questions')
def import_questions():
    """
    Import questions from JSON file.
    """
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                data = json.load(file)
                imported_count = 0
                
                # Import based on step
                step = request.form.get('step', 'step1')
                
                if step == 'step1' and 'step1_questions' in data:
                    for q_data in data['step1_questions']:
                        question = Step1Question(
                            question_text=q_data['question_text'],
                            question_type=q_data.get('question_type', 'technical'),
                            category=q_data.get('category', 'programming'),
                            difficulty=q_data.get('difficulty', 'medium'),
                            options=json.dumps(q_data.get('options', [])),
                            correct_answer=q_data['correct_answer'],
                            explanation=q_data.get('explanation', ''),
                            points=q_data.get('points', 1),
                            is_active=q_data.get('is_active', True)
                        )
                        db.session.add(question)
                        imported_count += 1
                
                elif step == 'step2' and 'step2_questions' in data:
                    for q_data in data['step2_questions']:
                        question = Step2Question(
                            title=q_data['title'],
                            content=q_data['content'],
                            category=q_data.get('category', 'programming'),
                            difficulty=q_data.get('difficulty', 'medium'),
                            time_minutes=q_data.get('time_minutes', 15),
                            evaluation_criteria=json.dumps(q_data.get('evaluation_criteria', [])),
                            related_technologies=json.dumps(q_data.get('related_technologies', [])),
                            is_active=q_data.get('is_active', True)
                        )
                        db.session.add(question)
                        imported_count += 1
                
                elif step == 'step3' and 'step3_questions' in data:
                    for q_data in data['step3_questions']:
                        question = Step3Question(
                            title=q_data['title'],
                            content=q_data['content'],
                            question_type=q_data.get('question_type', 'cto'),
                            category=q_data.get('category', 'leadership'),
                            time_minutes=q_data.get('time_minutes', 5),
                            evaluation_criteria=json.dumps(q_data.get('evaluation_criteria', [])),
                            is_active=q_data.get('is_active', True)
                        )
                        db.session.add(question)
                        imported_count += 1
                
                db.session.commit()
                flash(f'{imported_count} questions imported successfully.', 'success')
                
            except Exception as e:
                flash(f'Error importing questions: {str(e)}', 'error')
        
        else:
            flash('Invalid file format. Please upload a JSON file.', 'error')
    
    return render_template('questions/import.html')

@questions_bp.route('/questions/<step>/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('edit_question')
def edit_question(step, question_id):
    """
    Edit question.
    """
    if step == 'step1':
        question = Step1Question.query.get_or_404(question_id)
        form = Step1QuestionForm(obj=question)
        template = 'questions/edit_step1.html'
    elif step == 'step2':
        question = Step2Question.query.get_or_404(question_id)
        form = Step2QuestionForm(obj=question)
        template = 'questions/edit_step2.html'
    elif step == 'step3':
        question = Step3Question.query.get_or_404(question_id)
        form = Step3QuestionForm(obj=question)
        template = 'questions/edit_step3.html'
    else:
        flash('Invalid step specified.', 'error')
        return redirect(url_for('questions.question_bank'))
    
    if form.validate_on_submit():
        # Update question fields
        for field in form:
            if field.name not in ['csrf_token', 'submit']:
                setattr(question, field.name, field.data)
        
        db.session.commit()
        flash('Question updated successfully.', 'success')
        return redirect(url_for('questions.question_bank', step=step))
    
    return render_template(template, form=form, question=question, step=step)

@questions_bp.route('/questions/<step>/<int:question_id>/delete', methods=['POST'])
@login_required
@hr_required
@audit_action('delete_question')
def delete_question(step, question_id):
    """
    Delete question.
    """
    if step == 'step1':
        question = Step1Question.query.get_or_404(question_id)
    elif step == 'step2':
        question = Step2Question.query.get_or_404(question_id)
    elif step == 'step3':
        question = Step3Question.query.get_or_404(question_id)
    else:
        flash('Invalid step specified.', 'error')
        return redirect(url_for('questions.question_bank'))
    
    db.session.delete(question)
    db.session.commit()
    
    flash('Question deleted successfully.', 'success')
    return redirect(url_for('questions.question_bank', step=step))

@questions_bp.route('/questions/<step>/<int:question_id>/duplicate', methods=['POST'])
@login_required
@hr_required
@audit_action('duplicate_question')
def duplicate_question(step, question_id):
    """
    Duplicate question.
    """
    if step == 'step1':
        original = Step1Question.query.get_or_404(question_id)
        question = Step1Question(
            question_text=original.question_text + ' (Copy)',
            question_type=original.question_type,
            category=original.category,
            difficulty=original.difficulty,
            options=original.options,
            correct_answer=original.correct_answer,
            explanation=original.explanation,
            points=original.points,
            is_active=False  # Start as inactive
        )
    elif step == 'step2':
        original = Step2Question.query.get_or_404(question_id)
        question = Step2Question(
            title=original.title + ' (Copy)',
            content=original.content,
            category=original.category,
            difficulty=original.difficulty,
            time_minutes=original.time_minutes,
            evaluation_criteria=original.evaluation_criteria,
            related_technologies=original.related_technologies,
            is_active=False
        )
    elif step == 'step3':
        original = Step3Question.query.get_or_404(question_id)
        question = Step3Question(
            title=original.title + ' (Copy)',
            content=original.content,
            question_type=original.question_type,
            category=original.category,
            time_minutes=original.time_minutes,
            evaluation_criteria=original.evaluation_criteria,
            is_active=False
        )
    else:
        flash('Invalid step specified.', 'error')
        return redirect(url_for('questions.question_bank'))
    
    db.session.add(question)
    db.session.commit()
    
    flash('Question duplicated successfully.', 'success')
    return redirect(url_for('questions.question_bank', step=step))

@questions_bp.route('/questions/bulk-action', methods=['POST'])
@login_required
@hr_required
@audit_action('bulk_question_action')
def bulk_action():
    """
    Bulk actions on questions (activate, deactivate, delete).
    """
    action = request.form.get('action')
    question_ids = request.form.getlist('question_ids')
    step = request.form.get('step', 'step1')
    
    if not question_ids:
        flash('No questions selected.', 'error')
        return redirect(url_for('questions.question_bank', step=step))
    
    if step == 'step1':
        questions = Step1Question.query.filter(Step1Question.id.in_(question_ids)).all()
    elif step == 'step2':
        questions = Step2Question.query.filter(Step2Question.id.in_(question_ids)).all()
    elif step == 'step3':
        questions = Step3Question.query.filter(Step3Question.id.in_(question_ids)).all()
    else:
        flash('Invalid step specified.', 'error')
        return redirect(url_for('questions.question_bank'))
    
    if action == 'activate':
        for question in questions:
            question.is_active = True
        flash(f'{len(questions)} questions activated.', 'success')
    elif action == 'deactivate':
        for question in questions:
            question.is_active = False
        flash(f'{len(questions)} questions deactivated.', 'success')
    elif action == 'delete':
        for question in questions:
            db.session.delete(question)
        flash(f'{len(questions)} questions deleted.', 'success')
    else:
        flash('Invalid action specified.', 'error')
        return redirect(url_for('questions.question_bank', step=step))
    
    db.session.commit()
    return redirect(url_for('questions.question_bank', step=step))

@questions_bp.route('/questions/statistics')
@login_required
@hr_required
@audit_action('view_question_statistics')
def question_statistics():
    """
    Question statistics and analytics.
    """
    # Get statistics for each step
    step1_stats = {
        'total': Step1Question.query.count(),
        'active': Step1Question.query.filter_by(is_active=True).count(),
        'iq': Step1Question.query.filter_by(question_type='iq').count(),
        'technical': Step1Question.query.filter_by(question_type='technical').count(),
        'by_difficulty': {
            'easy': Step1Question.query.filter_by(difficulty='easy').count(),
            'medium': Step1Question.query.filter_by(difficulty='medium').count(),
            'hard': Step1Question.query.filter_by(difficulty='hard').count()
        }
    }
    
    step2_stats = {
        'total': Step2Question.query.count(),
        'active': Step2Question.query.filter_by(is_active=True).count(),
        'by_difficulty': {
            'easy': Step2Question.query.filter_by(difficulty='easy').count(),
            'medium': Step2Question.query.filter_by(difficulty='medium').count(),
            'hard': Step2Question.query.filter_by(difficulty='hard').count()
        }
    }
    
    step3_stats = {
        'total': Step3Question.query.count(),
        'active': Step3Question.query.filter_by(is_active=True).count(),
        'cto': Step3Question.query.filter_by(question_type='cto').count(),
        'ceo': Step3Question.query.filter_by(question_type='ceo').count()
    }
    
    return render_template('questions/statistics.html',
                         step1_stats=step1_stats,
                         step2_stats=step2_stats,
                         step3_stats=step3_stats)

# Helper functions
def allowed_file(filename: str) -> bool:
    """
    Check if file extension is allowed.
    
    Args:
        filename (str): Filename to check
        
    Returns:
        bool: True if allowed
    """
    ALLOWED_EXTENSIONS = {'json'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS 