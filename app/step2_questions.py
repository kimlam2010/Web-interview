"""
Step 2 Question Management Module

Manages technical interview questions for Step 2 with position-specific filtering,
difficulty classification, time allocation, and evaluation criteria.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func
from app.models import db, Step2Question, Position, User
from app.decorators import hr_required, interviewer_required, admin_required
from app.security import audit_log, rate_limit, security_check

step2_questions_bp = Blueprint('step2_questions', __name__)


class Step2QuestionManager:
    """
    Manager class for Step 2 question operations.
    
    Handles question creation, filtering, difficulty classification,
    time allocation, and evaluation criteria management.
    """
    
    # Question categories for Step 2
    CATEGORIES = {
        'technical_skills': 'Kỹ năng kỹ thuật',
        'problem_solving': 'Giải quyết vấn đề',
        'system_design': 'Thiết kế hệ thống',
        'coding_practice': 'Thực hành lập trình',
        'database_design': 'Thiết kế cơ sở dữ liệu',
        'api_design': 'Thiết kế API',
        'testing_strategies': 'Chiến lược kiểm thử',
        'deployment_devops': 'Triển khai và DevOps',
        'code_review': 'Code Review',
        'architecture_patterns': 'Mẫu kiến trúc'
    }
    
    # Difficulty levels
    DIFFICULTY_LEVELS = {
        'beginner': 'Cơ bản',
        'intermediate': 'Trung bình', 
        'advanced': 'Nâng cao',
        'expert': 'Chuyên gia'
    }
    
    # Time allocation per difficulty
    TIME_ALLOCATION = {
        'beginner': 5,      # 5 minutes
        'intermediate': 8,  # 8 minutes
        'advanced': 12,     # 12 minutes
        'expert': 15        # 15 minutes
    }
    
    # Evaluation criteria
    EVALUATION_CRITERIA = {
        'technical_accuracy': 'Độ chính xác kỹ thuật',
        'problem_understanding': 'Hiểu vấn đề',
        'solution_quality': 'Chất lượng giải pháp',
        'code_quality': 'Chất lượng code',
        'communication': 'Khả năng giao tiếp',
        'time_management': 'Quản lý thời gian',
        'creativity': 'Tính sáng tạo',
        'best_practices': 'Tuân thủ best practices'
    }
    
    @classmethod
    def create_step2_question(cls, data: Dict[str, Any]) -> Step2Question:
        """
        Create a new Step 2 question.
        
        Args:
            data: Question data dictionary
            
        Returns:
            Question: Created question object
        """
        question = Step2Question(
            step=2,
            category=data['category'],
            content=data['content'],
            difficulty=data['difficulty'],
            time_allocation=cls.TIME_ALLOCATION.get(data['difficulty'], 8),
            evaluation_criteria=json.dumps(data.get('evaluation_criteria', [])),
            position_specific=data.get('position_specific', False),
            position_id=data.get('position_id'),
            created_by=current_user.id,
            is_active=True
        )
        
        db.session.add(question)
        db.session.commit()
        
        return question
    
    @classmethod
    def get_questions_by_position(cls, position_id: int, 
                                difficulty: Optional[str] = None,
                                category: Optional[str] = None,
                                limit: int = 8) -> List[Step2Question]:
        """
        Get Step 2 questions filtered by position and criteria.
        
        Args:
            position_id: Position ID to filter by
            difficulty: Optional difficulty filter
            category: Optional category filter
            limit: Maximum number of questions to return
            
        Returns:
            List[Question]: Filtered questions
        """
        query = Step2Question.query.filter(
            and_(
                Step2Question.step == 2,
                Step2Question.is_active == True,
                or_(
                    Step2Question.position_specific == False,  # General questions
                    Step2Question.position_id == position_id   # Position-specific questions
                )
            )
        )
        
        if difficulty:
            query = query.filter(Step2Question.difficulty == difficulty)
        
        if category:
            query = query.filter(Step2Question.category == category)
        
        return query.order_by(func.random()).limit(limit).all()
    
    @classmethod
    def get_question_statistics(cls, position_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get statistics for Step 2 questions.
        
        Args:
            position_id: Optional position ID to filter by
            
        Returns:
            Dict: Statistics data
        """
        query = Step2Question.query.filter(Step2Question.step == 2)
        
        if position_id:
            query = query.filter(
                or_(
                    Step2Question.position_specific == False,
                    Step2Question.position_id == position_id
                )
            )
        
        total_questions = query.count()
        
        # Count by difficulty
        difficulty_stats = db.session.query(
            Step2Question.difficulty,
            func.count(Step2Question.id)
        ).filter(
            Step2Question.step == 2
        ).group_by(Step2Question.difficulty).all()
        
        # Count by category
        category_stats = db.session.query(
            Step2Question.category,
            func.count(Step2Question.id)
        ).filter(
            Step2Question.step == 2
        ).group_by(Step2Question.category).all()
        
        return {
            'total_questions': total_questions,
            'difficulty_distribution': dict(difficulty_stats),
            'category_distribution': dict(category_stats),
            'average_time_allocation': query.with_entities(
                func.avg(Step2Question.time_allocation)
            ).scalar() or 0
        }
    
    @classmethod
    def update_question_usage(cls, question_id: int, 
                            usage_data: Dict[str, Any]) -> None:
        """
        Update question usage statistics.
        
        Args:
            question_id: Question ID
            usage_data: Usage statistics data
        """
        question = Step2Question.query.get(question_id)
        if question:
            current_usage = json.loads(question.usage_statistics or '{}')
            current_usage.update(usage_data)
            question.usage_statistics = json.dumps(current_usage)
            question.last_used = datetime.utcnow()
            db.session.commit()


@step2_questions_bp.route('/step2/questions')
@login_required
@hr_required
@rate_limit('api')
@audit_log('view_step2_questions')
def list_step2_questions():
    """List all Step 2 questions with filtering options."""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    position_id = request.args.get('position_id', type=int)
    
    query = Step2Question.query.filter(Step2Question.step == 2)
    
    if category:
        query = query.filter(Step2Question.category == category)
    if difficulty:
        query = query.filter(Step2Question.difficulty == difficulty)
    if position_id:
        query = query.filter(
            or_(
                Step2Question.position_specific == False,
                Step2Question.position_id == position_id
            )
        )
    
    questions = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    positions = Position.query.all()
    statistics = Step2QuestionManager.get_question_statistics(position_id)
    
    return render_template('step2_questions/list.html',
                         questions=questions,
                         positions=positions,
                         statistics=statistics,
                         categories=Step2QuestionManager.CATEGORIES,
                         difficulty_levels=Step2QuestionManager.DIFFICULTY_LEVELS)


@step2_questions_bp.route('/step2/questions/create', methods=['GET', 'POST'])
@login_required
@hr_required
@rate_limit('api')
@audit_log('create_step2_question')
def create_step2_question():
    """Create a new Step 2 question."""
    if request.method == 'POST':
        try:
            data = {
                'category': request.form['category'],
                'content': request.form['content'],
                'difficulty': request.form['difficulty'],
                'evaluation_criteria': request.form.getlist('evaluation_criteria'),
                'position_specific': 'position_specific' in request.form,
                'position_id': request.form.get('position_id', type=int) if 'position_specific' in request.form else None
            }
            
            question = Step2QuestionManager.create_step2_question(data)
            
            flash('Câu hỏi Step 2 đã được tạo thành công!', 'success')
            return redirect(url_for('step2_questions.list_step2_questions'))
            
        except Exception as e:
            flash(f'Lỗi khi tạo câu hỏi: {str(e)}', 'error')
    
    positions = Position.query.all()
    
    return render_template('step2_questions/create.html',
                         categories=Step2QuestionManager.CATEGORIES,
                         difficulty_levels=Step2QuestionManager.DIFFICULTY_LEVELS,
                         evaluation_criteria=Step2QuestionManager.EVALUATION_CRITERIA,
                         time_allocation=Step2QuestionManager.TIME_ALLOCATION,
                         positions=positions)


@step2_questions_bp.route('/step2/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_required
@rate_limit('api')
@audit_log('edit_step2_question')
def edit_step2_question(question_id):
    """Edit an existing Step 2 question."""
    question = Step2Question.query.get_or_404(question_id)
    
    if question.step != 2:
        flash('Câu hỏi này không phải là Step 2 question!', 'error')
        return redirect(url_for('step2_questions.list_step2_questions'))
    
    if request.method == 'POST':
        try:
            question.category = request.form['category']
            question.content = request.form['content']
            question.difficulty = request.form['difficulty']
            question.evaluation_criteria = json.dumps(
                request.form.getlist('evaluation_criteria')
            )
            question.position_specific = 'position_specific' in request.form
            question.position_id = request.form.get('position_id', type=int) if 'position_specific' in request.form else None
            question.time_allocation = Step2QuestionManager.TIME_ALLOCATION.get(
                request.form['difficulty'], 8
            )
            question.updated_at = datetime.utcnow()
            question.updated_by = current_user.id
            
            db.session.commit()
            
            flash('Câu hỏi Step 2 đã được cập nhật thành công!', 'success')
            return redirect(url_for('step2_questions.list_step2_questions'))
            
        except Exception as e:
            flash(f'Lỗi khi cập nhật câu hỏi: {str(e)}', 'error')
    
    positions = Position.query.all()
    current_criteria = json.loads(question.evaluation_criteria or '[]')
    
    return render_template('step2_questions/edit.html',
                         question=question,
                         categories=Step2QuestionManager.CATEGORIES,
                         difficulty_levels=Step2QuestionManager.DIFFICULTY_LEVELS,
                         evaluation_criteria=Step2QuestionManager.EVALUATION_CRITERIA,
                         time_allocation=Step2QuestionManager.TIME_ALLOCATION,
                         positions=positions,
                         current_criteria=current_criteria)


@step2_questions_bp.route('/step2/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
@rate_limit('api')
@audit_log('delete_step2_question')
def delete_step2_question(question_id):
    """Delete a Step 2 question."""
    question = Step2Question.query.get_or_404(question_id)
    
    if question.step != 2:
        flash('Câu hỏi này không phải là Step 2 question!', 'error')
        return redirect(url_for('step2_questions.list_step2_questions'))
    
    try:
        db.session.delete(question)
        db.session.commit()
        
        flash('Câu hỏi Step 2 đã được xóa thành công!', 'success')
        
    except Exception as e:
        flash(f'Lỗi khi xóa câu hỏi: {str(e)}', 'error')
    
    return redirect(url_for('step2_questions.list_step2_questions'))


@step2_questions_bp.route('/step2/questions/import', methods=['GET', 'POST'])
@login_required
@hr_required
@rate_limit('upload')
@audit_log('import_step2_questions')
def import_step2_questions():
    """Import Step 2 questions from JSON file."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Không có file được chọn!', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Không có file được chọn!', 'error')
            return redirect(request.url)
        
        if not file.filename.endswith('.json'):
            flash('Chỉ chấp nhận file JSON!', 'error')
            return redirect(request.url)
        
        try:
            data = json.load(file)
            imported_count = 0
            
            for question_data in data.get('questions', []):
                question_data['step'] = 2
                question = Step2QuestionManager.create_step2_question(question_data)
                imported_count += 1
            
            flash(f'Đã import thành công {imported_count} câu hỏi Step 2!', 'success')
            return redirect(url_for('step2_questions.list_step2_questions'))
            
        except Exception as e:
            flash(f'Lỗi khi import file: {str(e)}', 'error')
    
    return render_template('step2_questions/import.html')


@step2_questions_bp.route('/step2/questions/export')
@login_required
@hr_required
@rate_limit('export')
@audit_log('export_step2_questions')
def export_step2_questions():
    """Export Step 2 questions to JSON."""
    try:
        questions = Step2Question.query.filter(Step2Question.step == 2).all()
        
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'total_questions': len(questions),
            'questions': []
        }
        
        for question in questions:
            question_data = {
                'category': question.category,
                'content': question.content,
                'difficulty': question.difficulty,
                'time_allocation': question.time_allocation,
                'evaluation_criteria': json.loads(question.evaluation_criteria or '[]'),
                'position_specific': question.position_specific,
                'position_id': question.position_id,
                'is_active': question.is_active
            }
            export_data['questions'].append(question_data)
        
        response = jsonify(export_data)
        response.headers['Content-Disposition'] = 'attachment; filename=step2_questions.json'
        return response
        
    except Exception as e:
        flash(f'Lỗi khi export: {str(e)}', 'error')
        return redirect(url_for('step2_questions.list_step2_questions'))


@step2_questions_bp.route('/step2/questions/statistics')
@login_required
@hr_required
@rate_limit('api')
def question_statistics():
    """Display Step 2 question statistics."""
    position_id = request.args.get('position_id', type=int)
    statistics = Step2QuestionManager.get_question_statistics(position_id)
    
    # Get usage statistics
    usage_query = Step2Question.query.filter(
        and_(
            Step2Question.step == 2,
            Step2Question.usage_statistics.isnot(None)
        )
    )
    
    if position_id:
        usage_query = usage_query.filter(
            or_(
                Step2Question.position_specific == False,
                Step2Question.position_id == position_id
            )
        )
    
    questions_with_usage = usage_query.all()
    
    usage_stats = {
        'total_used': len(questions_with_usage),
        'avg_usage_count': 0,
        'most_used_questions': []
    }
    
    if questions_with_usage:
        total_usage = 0
        for question in questions_with_usage:
            usage_data = json.loads(question.usage_statistics or '{}')
            usage_count = usage_data.get('usage_count', 0)
            total_usage += usage_count
        
        usage_stats['avg_usage_count'] = total_usage / len(questions_with_usage)
        
        # Get most used questions
        questions_with_usage.sort(
            key=lambda q: json.loads(q.usage_statistics or '{}').get('usage_count', 0),
            reverse=True
        )
        usage_stats['most_used_questions'] = questions_with_usage[:10]
    
    positions = Position.query.all()
    
    return render_template('step2_questions/statistics.html',
                         statistics=statistics,
                         usage_stats=usage_stats,
                         positions=positions,
                         categories=Step2QuestionManager.CATEGORIES,
                         difficulty_levels=Step2QuestionManager.DIFFICULTY_LEVELS)


@step2_questions_bp.route('/api/step2/questions/filter')
@login_required
@rate_limit('api')
def api_filter_questions():
    """API endpoint for filtering Step 2 questions."""
    position_id = request.args.get('position_id', type=int)
    difficulty = request.args.get('difficulty')
    category = request.args.get('category')
    limit = request.args.get('limit', 8, type=int)
    
    questions = Step2QuestionManager.get_questions_by_position(
        position_id, difficulty, category, limit
    )
    
    question_data = []
    for question in questions:
        data = {
            'id': question.id,
            'category': question.category,
            'content': question.content,
            'difficulty': question.difficulty,
            'time_allocation': question.time_allocation,
            'evaluation_criteria': json.loads(question.evaluation_criteria or '[]'),
            'position_specific': question.position_specific,
            'position_id': question.position_id
        }
        question_data.append(data)
    
    return jsonify({
        'questions': question_data,
        'total': len(question_data),
        'filters': {
            'position_id': position_id,
            'difficulty': difficulty,
            'category': category,
            'limit': limit
        }
    })


@step2_questions_bp.route('/api/step2/questions/<int:question_id>/usage', methods=['POST'])
@login_required
@rate_limit('api')
def api_update_question_usage(question_id):
    """API endpoint for updating question usage statistics."""
    try:
        usage_data = request.get_json()
        Step2QuestionManager.update_question_usage(question_id, usage_data)
        
        return jsonify({'success': True, 'message': 'Usage statistics updated'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@step2_questions_bp.route('/step2/questions/bulk-operations', methods=['POST'])
@login_required
@hr_required
@rate_limit('api')
@audit_log('bulk_operations_step2_questions')
def bulk_operations():
    """Perform bulk operations on Step 2 questions."""
    action = request.form.get('action')
    question_ids = request.form.getlist('question_ids')
    
    if not question_ids:
        flash('Vui lòng chọn ít nhất một câu hỏi!', 'error')
        return redirect(url_for('step2_questions.list_step2_questions'))
    
    try:
        questions = Step2Question.query.filter(
            and_(
                Step2Question.id.in_(question_ids),
                Step2Question.step == 2
            )
        ).all()
        
        if action == 'activate':
            for question in questions:
                question.is_active = True
            message = f'Đã kích hoạt {len(questions)} câu hỏi!'
            
        elif action == 'deactivate':
            for question in questions:
                question.is_active = False
            message = f'Đã vô hiệu hóa {len(questions)} câu hỏi!'
            
        elif action == 'delete':
            for question in questions:
                db.session.delete(question)
            message = f'Đã xóa {len(questions)} câu hỏi!'
            
        else:
            flash('Hành động không hợp lệ!', 'error')
            return redirect(url_for('step2_questions.list_step2_questions'))
        
        db.session.commit()
        flash(message, 'success')
        
    except Exception as e:
        flash(f'Lỗi khi thực hiện bulk operations: {str(e)}', 'error')
    
    return redirect(url_for('step2_questions.list_step2_questions')) 