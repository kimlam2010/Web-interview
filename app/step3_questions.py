"""
Step 3 Question Management Module

Manages executive interview questions for Step 3 with CTO vs CEO separation,
difficulty scaling, evaluation criteria, and interview structure management.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func, desc
from app.models import db, Step3Question, Step3InterviewStructure, Step3ExecutiveFeedback, Position, User
from app.decorators import hr_required, interviewer_required, executive_required, admin_required
from app.security import audit_log, rate_limit, security_check

step3_questions_bp = Blueprint('step3_questions', __name__)


class Step3QuestionManager:
    """Manager class for Step 3 question operations."""
    
    @staticmethod
    def create_step3_question(data: Dict[str, Any]) -> Step3Question:
        """Create a new Step 3 question."""
        question = Step3Question(
            content=data['content'],
            question_type=data['question_type'],
            category=data['category'],
            assigned_to=data['assigned_to'],
            position_id=data.get('position_id'),
            difficulty_level=data['difficulty_level'],
            time_allocation=data.get('time_allocation', 10),
            priority_score=data.get('priority_score', 1),
            technical_weight=data.get('technical_weight', 0.6),
            leadership_weight=data.get('leadership_weight', 0.2),
            cultural_weight=data.get('cultural_weight', 0.2),
            expected_key_points=json.dumps(data.get('expected_key_points', [])),
            scoring_rubric=json.dumps(data.get('scoring_rubric', {})),
            sample_answers=json.dumps(data.get('sample_answers', [])),
            created_by=current_user.id
        )
        
        db.session.add(question)
        db.session.commit()
        
        return question
    
    @staticmethod
    def get_questions_by_position(position_id: int, assigned_to: Optional[str] = None) -> List[Step3Question]:
        """Get Step 3 questions by position and executive assignment."""
        query = Step3Question.query.filter(
            and_(
                Step3Question.position_id == position_id,
                Step3Question.is_active == True
            )
        )
        
        if assigned_to:
            query = query.filter(Step3Question.assigned_to == assigned_to)
        
        return query.order_by(Step3Question.priority_score.desc()).all()
    
    @staticmethod
    def get_questions_by_difficulty(difficulty: str, limit: int = 10) -> List[Step3Question]:
        """Get Step 3 questions by difficulty level."""
        return Step3Question.query.filter(
            and_(
                Step3Question.difficulty_level == difficulty,
                Step3Question.is_active == True
            )
        ).limit(limit).all()
    
    @staticmethod
    def get_questions_for_executive(executive_role: str, position_id: int, count: int = 3) -> List[Step3Question]:
        """Get questions for specific executive (CTO/CEO) with balanced difficulty."""
        # Get questions assigned to this executive
        assigned_filter = 'both' if executive_role in ['cto', 'ceo'] else executive_role
        
        questions = Step3Question.query.filter(
            and_(
                Step3Question.position_id == position_id,
                Step3Question.assigned_to.in_(['both', assigned_filter]),
                Step3Question.is_active == True
            )
        ).order_by(Step3Question.priority_score.desc()).all()
        
        # Balance by difficulty
        difficulty_counts = {'beginner': 0, 'intermediate': 0, 'advanced': 0, 'expert': 0}
        selected_questions = []
        
        for question in questions:
            if len(selected_questions) >= count:
                break
                
            difficulty = question.difficulty_level
            if difficulty_counts[difficulty] < count // 4:  # Distribute evenly
                selected_questions.append(question)
                difficulty_counts[difficulty] += 1
        
        # Fill remaining slots
        for question in questions:
            if len(selected_questions) >= count:
                break
            if question not in selected_questions:
                selected_questions.append(question)
        
        return selected_questions[:count]
    
    @staticmethod
    def update_question_stats(question_id: int, score: float, passed: bool):
        """Update question usage statistics."""
        question = Step3Question.query.get(question_id)
        if question:
            question.update_usage_stats(score, passed)
            db.session.commit()
    
    @staticmethod
    def get_question_statistics() -> Dict[str, Any]:
        """Get comprehensive question statistics."""
        stats = db.session.query(
            Step3Question.difficulty_level,
            Step3Question.assigned_to,
            func.count(Step3Question.id).label('count'),
            func.avg(Step3Question.average_score).label('avg_score'),
            func.avg(Step3Question.success_rate).label('avg_success_rate')
        ).filter(Step3Question.is_active == True).group_by(
            Step3Question.difficulty_level,
            Step3Question.assigned_to
        ).all()
        
        return {
            'difficulty_stats': {row.difficulty_level: row.count for row in stats},
            'assignment_stats': {row.assigned_to: row.count for row in stats},
            'performance_stats': {
                row.difficulty_level: {
                    'avg_score': float(row.avg_score or 0),
                    'avg_success_rate': float(row.avg_success_rate or 0)
                } for row in stats
            }
        }


class Step3InterviewStructureManager:
    """Manager class for Step 3 interview structure operations."""
    
    @staticmethod
    def create_interview_structure(data: Dict[str, Any]) -> Step3InterviewStructure:
        """Create a new interview structure."""
        structure = Step3InterviewStructure(
            name=data['name'],
            description=data.get('description'),
            total_duration=data.get('total_duration', 60),
            cto_duration=data.get('cto_duration', 30),
            ceo_duration=data.get('ceo_duration', 30),
            cto_questions_count=data.get('cto_questions_count', 3),
            ceo_questions_count=data.get('ceo_questions_count', 3),
            beginner_ratio=data.get('beginner_ratio', 0.2),
            intermediate_ratio=data.get('intermediate_ratio', 0.4),
            advanced_ratio=data.get('advanced_ratio', 0.3),
            expert_ratio=data.get('expert_ratio', 0.1),
            position_id=data.get('position_id'),
            created_by=current_user.id
        )
        
        db.session.add(structure)
        db.session.commit()
        
        return structure
    
    @staticmethod
    def get_structure_for_position(position_id: int) -> Optional[Step3InterviewStructure]:
        """Get interview structure for specific position."""
        return Step3InterviewStructure.query.filter(
            and_(
                Step3InterviewStructure.position_id == position_id,
                Step3InterviewStructure.is_active == True
            )
        ).first()
    
    @staticmethod
    def generate_question_set(structure: Step3InterviewStructure) -> Dict[str, List[Step3Question]]:
        """Generate balanced question set for interview structure."""
        position_id = structure.position_id
        
        # Get questions for CTO
        cto_questions = Step3QuestionManager.get_questions_for_executive(
            'cto', position_id, structure.cto_questions_count
        )
        
        # Get questions for CEO
        ceo_questions = Step3QuestionManager.get_questions_for_executive(
            'ceo', position_id, structure.ceo_questions_count
        )
        
        return {
            'cto_questions': cto_questions,
            'ceo_questions': ceo_questions,
            'total_duration': structure.total_duration,
            'cto_duration': structure.cto_duration,
            'ceo_duration': structure.ceo_duration
        }


# Route Definitions

@step3_questions_bp.route('/step3/questions')
@login_required
@hr_required
@rate_limit('step3_questions', {'requests': 100, 'window': 3600})
@audit_log('view_step3_questions')
def list_step3_questions():
    """List all Step 3 questions with filtering."""
    # Get filter parameters
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    assigned_to = request.args.get('assigned_to')
    position_id = request.args.get('position_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query
    query = Step3Question.query
    
    if category:
        query = query.filter(Step3Question.category == category)
    if difficulty:
        query = query.filter(Step3Question.difficulty_level == difficulty)
    if assigned_to:
        query = query.filter(Step3Question.assigned_to == assigned_to)
    if position_id:
        query = query.filter(Step3Question.position_id == position_id)
    
    # Get paginated results
    questions = query.filter(Step3Question.is_active == True).order_by(
        desc(Step3Question.priority_score)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get filter options
    categories = db.session.query(Step3Question.category).distinct().all()
    difficulties = ['beginner', 'intermediate', 'advanced', 'expert']
    assignments = ['cto', 'ceo', 'both']
    positions = Position.query.filter(Position.is_active == True).all()
    
    return render_template('step3_questions/list.html',
                         questions=questions,
                         categories=categories,
                         difficulties=difficulties,
                         assignments=assignments,
                         positions=positions)


@step3_questions_bp.route('/step3/questions/create', methods=['GET', 'POST'])
@login_required
@hr_required
@rate_limit('step3_questions', {'requests': 50, 'window': 3600})
@audit_log('create_step3_question')
def create_step3_question():
    """Create a new Step 3 question."""
    if request.method == 'POST':
        try:
            data = {
                'content': request.form['content'],
                'question_type': request.form['question_type'],
                'category': request.form['category'],
                'assigned_to': request.form['assigned_to'],
                'position_id': request.form.get('position_id', type=int),
                'difficulty_level': request.form['difficulty_level'],
                'time_allocation': request.form.get('time_allocation', type=int),
                'priority_score': request.form.get('priority_score', type=int),
                'technical_weight': request.form.get('technical_weight', type=float),
                'leadership_weight': request.form.get('leadership_weight', type=float),
                'cultural_weight': request.form.get('cultural_weight', type=float),
                'expected_key_points': request.form.get('expected_key_points', '').split('\n'),
                'scoring_rubric': json.loads(request.form.get('scoring_rubric', '{}')),
                'sample_answers': request.form.get('sample_answers', '').split('\n')
            }
            
            question = Step3QuestionManager.create_step3_question(data)
            flash('Câu hỏi Step 3 đã được tạo thành công!', 'success')
            return redirect(url_for('step3_questions.list_step3_questions'))
            
        except Exception as e:
            flash(f'Lỗi khi tạo câu hỏi: {str(e)}', 'error')
    
    positions = Position.query.filter(Position.is_active == True).all()
    return render_template('step3_questions/create.html', positions=positions)


@step3_questions_bp.route('/step3/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_required
@rate_limit('step3_questions', {'requests': 50, 'window': 3600})
@audit_log('edit_step3_question')
def edit_step3_question(question_id):
    """Edit an existing Step 3 question."""
    question = Step3Question.query.get_or_404(question_id)
    
    if request.method == 'POST':
        try:
            question.content = request.form['content']
            question.question_type = request.form['question_type']
            question.category = request.form['category']
            question.assigned_to = request.form['assigned_to']
            question.position_id = request.form.get('position_id', type=int)
            question.difficulty_level = request.form['difficulty_level']
            question.time_allocation = request.form.get('time_allocation', type=int)
            question.priority_score = request.form.get('priority_score', type=int)
            question.technical_weight = request.form.get('technical_weight', type=float)
            question.leadership_weight = request.form.get('leadership_weight', type=float)
            question.cultural_weight = request.form.get('cultural_weight', type=float)
            question.expected_key_points = json.dumps(request.form.get('expected_key_points', '').split('\n'))
            question.scoring_rubric = request.form.get('scoring_rubric', '{}')
            question.sample_answers = json.dumps(request.form.get('sample_answers', '').split('\n'))
            question.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Câu hỏi Step 3 đã được cập nhật thành công!', 'success')
            return redirect(url_for('step3_questions.list_step3_questions'))
            
        except Exception as e:
            flash(f'Lỗi khi cập nhật câu hỏi: {str(e)}', 'error')
    
    positions = Position.query.filter(Position.is_active == True).all()
    return render_template('step3_questions/edit.html', question=question, positions=positions)


@step3_questions_bp.route('/step3/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
@rate_limit('step3_questions', {'requests': 20, 'window': 3600})
@audit_log('delete_step3_question')
def delete_step3_question(question_id):
    """Delete a Step 3 question."""
    question = Step3Question.query.get_or_404(question_id)
    
    try:
        question.is_active = False
        db.session.commit()
        flash('Câu hỏi Step 3 đã được xóa thành công!', 'success')
    except Exception as e:
        flash(f'Lỗi khi xóa câu hỏi: {str(e)}', 'error')
    
    return redirect(url_for('step3_questions.list_step3_questions'))


@step3_questions_bp.route('/step3/questions/import', methods=['GET', 'POST'])
@login_required
@hr_required
@rate_limit('step3_questions', {'requests': 10, 'window': 3600})
@audit_log('import_step3_questions')
def import_step3_questions():
    """Import Step 3 questions from JSON."""
    if request.method == 'POST':
        try:
            file = request.files['file']
            if file and file.filename.endswith('.json'):
                data = json.loads(file.read())
                imported_count = 0
                
                for item in data:
                    question = Step3QuestionManager.create_step3_question(item)
                    imported_count += 1
                
                flash(f'Đã import thành công {imported_count} câu hỏi Step 3!', 'success')
                return redirect(url_for('step3_questions.list_step3_questions'))
            else:
                flash('Vui lòng chọn file JSON hợp lệ!', 'error')
                
        except Exception as e:
            flash(f'Lỗi khi import: {str(e)}', 'error')
    
    return render_template('step3_questions/import.html')


@step3_questions_bp.route('/step3/questions/export')
@login_required
@hr_required
@rate_limit('step3_questions', {'requests': 20, 'window': 3600})
@audit_log('export_step3_questions')
def export_step3_questions():
    """Export Step 3 questions to JSON."""
    try:
        questions = Step3Question.query.filter(Step3Question.is_active == True).all()
        
        export_data = []
        for question in questions:
            export_data.append({
                'content': question.content,
                'question_type': question.question_type,
                'category': question.category,
                'assigned_to': question.assigned_to,
                'position_id': question.position_id,
                'difficulty_level': question.difficulty_level,
                'time_allocation': question.time_allocation,
                'priority_score': question.priority_score,
                'technical_weight': question.technical_weight,
                'leadership_weight': question.leadership_weight,
                'cultural_weight': question.cultural_weight,
                'expected_key_points': question.get_expected_points(),
                'scoring_rubric': question.get_scoring_rubric(),
                'sample_answers': question.get_sample_answers()
            })
        
        from flask import Response
        response = Response(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            mimetype='application/json'
        )
        response.headers['Content-Disposition'] = 'attachment; filename=step3_questions.json'
        return response
        
    except Exception as e:
        flash(f'Lỗi khi export: {str(e)}', 'error')
        return redirect(url_for('step3_questions.list_step3_questions'))


@step3_questions_bp.route('/step3/questions/statistics')
@login_required
@hr_required
@rate_limit('step3_questions', {'requests': 50, 'window': 3600})
@audit_log('view_step3_question_statistics')
def question_statistics():
    """Display Step 3 question statistics."""
    try:
        stats = Step3QuestionManager.get_question_statistics()
        
        # Get additional statistics
        total_questions = Step3Question.query.filter(Step3Question.is_active == True).count()
        cto_questions = Step3Question.query.filter(
            and_(
                Step3Question.assigned_to.in_(['cto', 'both']),
                Step3Question.is_active == True
            )
        ).count()
        ceo_questions = Step3Question.query.filter(
            and_(
                Step3Question.assigned_to.in_(['ceo', 'both']),
                Step3Question.is_active == True
            )
        ).count()
        
        # Get top performing questions
        top_questions = Step3Question.query.filter(
            and_(
                Step3Question.is_active == True,
                Step3Question.times_used > 0
            )
        ).order_by(desc(Step3Question.average_score)).limit(10).all()
        
        return render_template('step3_questions/statistics.html',
                             stats=stats,
                             total_questions=total_questions,
                             cto_questions=cto_questions,
                             ceo_questions=ceo_questions,
                             top_questions=top_questions)
                             
    except Exception as e:
        flash(f'Lỗi khi tải thống kê: {str(e)}', 'error')
        return redirect(url_for('step3_questions.list_step3_questions'))


# API Endpoints

@step3_questions_bp.route('/api/step3/questions/filter')
@login_required
@rate_limit('api', {'requests': 1000, 'window': 3600})
def api_filter_questions():
    """API endpoint for filtering Step 3 questions."""
    try:
        category = request.args.get('category')
        difficulty = request.args.get('difficulty')
        assigned_to = request.args.get('assigned_to')
        position_id = request.args.get('position_id', type=int)
        
        query = Step3Question.query.filter(Step3Question.is_active == True)
        
        if category:
            query = query.filter(Step3Question.category == category)
        if difficulty:
            query = query.filter(Step3Question.difficulty_level == difficulty)
        if assigned_to:
            query = query.filter(Step3Question.assigned_to == assigned_to)
        if position_id:
            query = query.filter(Step3Question.position_id == position_id)
        
        questions = query.limit(50).all()
        
        return jsonify({
            'success': True,
            'questions': [{
                'id': q.id,
                'content': q.content,
                'question_type': q.question_type,
                'category': q.category,
                'assigned_to': q.assigned_to,
                'difficulty_level': q.difficulty_level,
                'time_allocation': q.time_allocation,
                'priority_score': q.priority_score,
                'average_score': q.average_score,
                'success_rate': q.success_rate
            } for q in questions]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@step3_questions_bp.route('/api/step3/questions/<int:question_id>/usage', methods=['POST'])
@login_required
@rate_limit('api', {'requests': 1000, 'window': 3600})
def api_update_usage_stats(question_id):
    """API endpoint for updating question usage statistics."""
    try:
        data = request.get_json()
        score = data.get('score', 0)
        passed = data.get('passed', False)
        
        Step3QuestionManager.update_question_stats(question_id, score, passed)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@step3_questions_bp.route('/api/step3/questions/generate-set')
@login_required
@executive_required
@rate_limit('api', {'requests': 100, 'window': 3600})
def api_generate_question_set():
    """API endpoint for generating question set for interview."""
    try:
        position_id = request.args.get('position_id', type=int)
        executive_role = request.args.get('executive_role')  # cto, ceo
        count = request.args.get('count', 3, type=int)
        
        if not position_id or not executive_role:
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
        
        questions = Step3QuestionManager.get_questions_for_executive(
            executive_role, position_id, count
        )
        
        return jsonify({
            'success': True,
            'questions': [{
                'id': q.id,
                'content': q.content,
                'question_type': q.question_type,
                'category': q.category,
                'difficulty_level': q.difficulty_level,
                'time_allocation': q.time_allocation,
                'technical_weight': q.technical_weight,
                'leadership_weight': q.leadership_weight,
                'cultural_weight': q.cultural_weight,
                'expected_key_points': q.get_expected_points(),
                'scoring_rubric': q.get_scoring_rubric()
            } for q in questions]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Interview Structure Routes

@step3_questions_bp.route('/step3/structures')
@login_required
@hr_required
@rate_limit('step3_questions', {'requests': 100, 'window': 3600})
@audit_log('view_step3_structures')
def list_interview_structures():
    """List all Step 3 interview structures."""
    structures = Step3InterviewStructure.query.filter(
        Step3InterviewStructure.is_active == True
    ).order_by(Step3InterviewStructure.name).all()
    
    positions = Position.query.filter(Position.is_active == True).all()
    
    return render_template('step3_questions/structures.html',
                         structures=structures,
                         positions=positions)


@step3_questions_bp.route('/step3/structures/create', methods=['GET', 'POST'])
@login_required
@hr_required
@rate_limit('step3_questions', {'requests': 50, 'window': 3600})
@audit_log('create_step3_structure')
def create_interview_structure():
    """Create a new Step 3 interview structure."""
    if request.method == 'POST':
        try:
            data = {
                'name': request.form['name'],
                'description': request.form.get('description'),
                'total_duration': request.form.get('total_duration', type=int),
                'cto_duration': request.form.get('cto_duration', type=int),
                'ceo_duration': request.form.get('ceo_duration', type=int),
                'cto_questions_count': request.form.get('cto_questions_count', type=int),
                'ceo_questions_count': request.form.get('ceo_questions_count', type=int),
                'beginner_ratio': request.form.get('beginner_ratio', type=float),
                'intermediate_ratio': request.form.get('intermediate_ratio', type=float),
                'advanced_ratio': request.form.get('advanced_ratio', type=float),
                'expert_ratio': request.form.get('expert_ratio', type=float),
                'position_id': request.form.get('position_id', type=int)
            }
            
            structure = Step3InterviewStructureManager.create_interview_structure(data)
            flash('Cấu trúc phỏng vấn Step 3 đã được tạo thành công!', 'success')
            return redirect(url_for('step3_questions.list_interview_structures'))
            
        except Exception as e:
            flash(f'Lỗi khi tạo cấu trúc: {str(e)}', 'error')
    
    positions = Position.query.filter(Position.is_active == True).all()
    return render_template('step3_questions/create_structure.html', positions=positions) 