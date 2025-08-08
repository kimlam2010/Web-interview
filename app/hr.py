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

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SelectField, TextAreaField, FileField, SubmitField, IntegerField, BooleanField, DateField
from wtforms.validators import DataRequired, Email, Length, Optional, URL, NumberRange
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from typing import List, Dict, Any

from . import db
from .models import Candidate, Position, User, AuditLog, InterviewEvaluation
from .decorators import hr_required, audit_action
from app.utils import log_audit_event, get_client_ip, send_email, send_interview_invitation
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


class ScheduleInterviewForm(FlaskForm):
    """Form để lên lịch phỏng vấn Step2/Step3."""
    step = SelectField('Bước', choices=[('step2', 'Step 2 - Technical'), ('step3', 'Step 3 - Executive')], validators=[DataRequired()])
    interviewer_id = SelectField('Người phỏng vấn', coerce=int, validators=[DataRequired()])
    interview_datetime = StringField('Thời gian (YYYY-MM-DDTHH:MM)', validators=[DataRequired()])
    meeting_link = StringField('Link phỏng vấn (tùy chọn)', validators=[Optional()])
    message = TextAreaField('Ghi chú gửi ứng viên (tùy chọn)', validators=[Optional()])
    submit = SubmitField('Lên lịch')


class PositionForm(FlaskForm):
    """Form tạo/sửa Position theo models.Position."""
    title = StringField('Chức danh', validators=[DataRequired(), Length(min=3, max=100)])
    department = SelectField('Phòng ban', validators=[DataRequired()])
    level = SelectField('Cấp bậc', validators=[DataRequired()])
    salary_min = IntegerField('Lương tối thiểu', validators=[Optional(), NumberRange(min=0)])
    salary_max = IntegerField('Lương tối đa', validators=[Optional(), NumberRange(min=0)])
    description = TextAreaField('Mô tả công việc', validators=[DataRequired(), Length(min=10)])
    required_skills = StringField('Kỹ năng yêu cầu (CSV)', validators=[Optional(), Length(max=500)])
    target_start_date = DateField('Ngày dự kiến bắt đầu', validators=[Optional()])
    hiring_urgency = IntegerField('Độ khẩn (1-5)', validators=[Optional(), NumberRange(min=1, max=5)], default=3)
    is_active = BooleanField('Đang tuyển', default=True)
    submit = SubmitField('Lưu vị trí')

@hr_bp.route('/')
@login_required
@hr_required
@audit_action('view_hr_dashboard')
def hr_dashboard():
    """Dashboard HR: cung cấp dữ liệu pipeline cho mini-chart."""
    total = Candidate.query.count()
    data = {
        'pending': Candidate.query.filter_by(status='pending').count(),
        'step1_completed': Candidate.query.filter_by(status='step1_completed').count(),
        'step2_completed': Candidate.query.filter_by(status='step2_completed').count(),
        'hired': Candidate.query.filter_by(status='hired').count(),
        'rejected': Candidate.query.filter_by(status='rejected').count(),
    }
    data['total'] = total
    return render_template('dashboard/hr_dashboard.html', pipeline_data=data)

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
                upload_dir = os.path.join('uploads', 'cv')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, cv_filename))
        
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
        
        # Create temporary credentials and email to candidate
        expiry_days = current_app.config.get('LINK_EXPIRATION_DAYS', {}).get('step1_default', 7)
        username, password = create_candidate_credentials(candidate, expiry_days=expiry_days)
        try:
            login_url = url_for('candidate_auth.candidate_login', _external=True)
            body = (
                f"Xin chào {candidate.get_full_name()},\n\n"
                f"Tài khoản làm bài Step 1 của bạn:\n"
                f"- Username: {username}\n- Password: {password}\n\n"
                f"Đường dẫn: {login_url}\n"
                f"Hạn sử dụng: {expiry_days} ngày.\n\nTrân trọng."
            )
            send_email(candidate.email, 'Thông tin làm bài Step 1', body)
        except Exception:
            pass
        flash('Candidate added và đã gửi thông tin Step 1 qua email (nếu cấu hình SMTP).', 'success')
        return redirect(url_for('hr.candidate_management'))
    
    return render_template('hr/add_candidate.html', form=form)


@hr_bp.route('/schedule/<int:candidate_id>', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('schedule_interview')
def schedule_interview(candidate_id: int):
    """Lên lịch phỏng vấn Step2/Step3 cho ứng viên và gửi email mời."""
    candidate = Candidate.query.get_or_404(candidate_id)
    form = ScheduleInterviewForm()
    # Nạp danh sách interviewer
    interviewers = User.query.filter(User.role.in_(['interviewer', 'cto', 'ceo'])).all()
    form.interviewer_id.choices = [(u.id, f"{u.get_full_name()} ({u.role})") for u in interviewers]

    if request.method == 'POST' and form.validate_on_submit():
        # Parse datetime-local string
        try:
            # Expect format YYYY-MM-DDTHH:MM
            dt = datetime.strptime(form.interview_datetime.data.strip(), '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Định dạng thời gian không hợp lệ. Vui lòng dùng YYYY-MM-DDTHH:MM', 'warning')
            return render_template('hr/schedule.html', form=form, candidate=candidate)

        # Tạo bản ghi InterviewEvaluation (điểm = 0 khi mới lên lịch)
        evaluation = InterviewEvaluation(
            candidate_id=candidate.id,
            interviewer_id=form.interviewer_id.data,
            step=form.step.data,
            score=0.0,
            interview_date=dt,
            notes=None,
        )

        # Lưu meeting_link/message vào notes dạng JSON để tra cứu sau
        extras = {}
        if form.meeting_link.data:
            extras['meeting_link'] = form.meeting_link.data.strip()
        if form.message.data:
            extras['message'] = form.message.data.strip()
        if extras:
            import json as _json
            evaluation.notes = _json.dumps(extras)

        db.session.add(evaluation)
        db.session.commit()

        # Gửi email mời ứng viên (phân biệt Step2/Step3)
        interviewer = User.query.get(form.interviewer_id.data)
        link_for_email = extras.get('meeting_link') if extras else ''
        subject_prefix = 'Step 2' if form.step.data == 'step2' else 'Step 3'
        send_ok = send_interview_invitation(
            candidate_email=candidate.email,
            candidate_name=candidate.get_full_name(),
            interview_link=link_for_email or url_for('dashboard.hr_dashboard', _external=True),
            interview_date=dt,
            interviewer_name=f"{subject_prefix} - {interviewer.get_full_name() if interviewer else 'Interviewer'}"
        )

        flash(
            ('Đã lên lịch phỏng vấn Step 2 và gửi email mời.' if form.step.data=='step2' else 'Đã lên lịch Step 3 và gửi email mời.')
            if send_ok else 'Đã lên lịch. Gửi email thất bại, vui lòng kiểm tra SMTP.',
            'success' if send_ok else 'warning'
        )
        return redirect(url_for('hr.candidate_management'))

    return render_template('hr/schedule.html', form=form, candidate=candidate)


@hr_bp.route('/candidates/export')
@login_required
@hr_required
@audit_action('export_candidates_csv')
def export_candidates_csv():
    """Xuất CSV danh sách ứng viên theo filter hiện tại."""
    # Tái sử dụng logic filter từ candidate_management
    search_term = request.args.get('search_term', '')
    position_filter = request.args.get('position_filter', '')
    status_filter = request.args.get('status_filter', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Candidate.query
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

    rows = query.order_by(Candidate.created_at.desc()).all()

    import csv
    from io import StringIO
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['first_name', 'last_name', 'email', 'phone', 'position_title', 'status', 'notes'])
    for c in rows:
        writer.writerow([
            c.first_name, c.last_name, c.email, c.phone,
            c.position.title if c.position else '', c.status, (c.notes or '').replace('\n', ' ')
        ])
    output = si.getvalue()

    from flask import Response
    return Response(
        output,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=candidates_export.csv'}
    )


@hr_bp.route('/candidates/import', methods=['POST'])
@login_required
@hr_required
@audit_action('import_candidates_csv')
def import_candidates_csv():
    """Nhập CSV ứng viên: tạo mới hoặc cập nhật theo email."""
    file = request.files.get('file')
    if not file or not file.filename.lower().endswith('.csv'):
        flash('Vui lòng chọn tệp CSV hợp lệ.', 'warning')
        return redirect(url_for('hr.candidate_management'))

    import csv
    from io import TextIOWrapper
    created, updated, errors = 0, 0, 0
    try:
        wrapper = TextIOWrapper(file, encoding='utf-8')
        reader = csv.DictReader(wrapper)
        for row in reader:
            try:
                email = (row.get('email') or '').strip().lower()
                if not email:
                    continue
                candidate = Candidate.query.filter_by(email=email).first()
                # Map position by title
                pos_title = (row.get('position_title') or '').strip()
                position = Position.query.filter_by(title=pos_title).first() if pos_title else None
                payload = {
                    'first_name': (row.get('first_name') or '').strip() or 'Unknown',
                    'last_name': (row.get('last_name') or '').strip() or 'Unknown',
                    'phone': (row.get('phone') or '').strip() or 'N/A',
                    'status': (row.get('status') or '').strip() or 'pending',
                    'notes': (row.get('notes') or '').strip() or None,
                }
                if position:
                    payload['position_id'] = position.id
                if candidate:
                    for k, v in payload.items():
                        setattr(candidate, k, v)
                    updated += 1
                else:
                    if not position:
                        # fallback: choose any active position
                        any_pos = Position.query.filter_by(is_active=True).first()
                        if any_pos:
                            payload['position_id'] = any_pos.id
                    new_cand = Candidate(email=email, **payload)
                    db.session.add(new_cand)
                    created += 1
            except Exception:
                errors += 1
        db.session.commit()
        flash(f'Import xong. Tạo mới: {created}, Cập nhật: {updated}, Lỗi: {errors}', 'success')
    except Exception:
        db.session.rollback()
        flash('Import thất bại. Kiểm tra định dạng CSV và mã hóa UTF-8.', 'danger')
    return redirect(url_for('hr.candidate_management'))


@hr_bp.route('/candidates/<int:candidate_id>/send_step3', methods=['POST'])
@login_required
@hr_required
@audit_action('send_step3_invitation')
def send_step3_invite(candidate_id: int):
    """Gửi lại thư mời Step3 cho ứng viên hiện có (dùng meeting_link mới nhất nếu có)."""
    candidate = Candidate.query.get_or_404(candidate_id)
    # Lấy evaluation Step3 mới nhất để lấy thời điểm/phỏng vấn viên/link
    evaluation = (
        InterviewEvaluation.query
        .filter_by(candidate_id=candidate_id, step='step3')
        .order_by(InterviewEvaluation.created_at.desc())
        .first()
    )
    if not evaluation:
        flash('Chưa có lịch Step 3 để gửi lại.', 'warning')
        return redirect(url_for('hr.candidate_management'))

    interviewer = User.query.get(evaluation.interviewer_id)
    meeting_link = ''
    try:
        import json as _json
        extras = _json.loads(evaluation.notes or '{}') if evaluation.notes else {}
        meeting_link = extras.get('meeting_link', '')
    except Exception:
        meeting_link = ''

    ok = send_interview_invitation(
        candidate_email=candidate.email,
        candidate_name=candidate.get_full_name(),
        interview_link=meeting_link or url_for('dashboard.hr_dashboard', _external=True),
        interview_date=evaluation.interview_date,
        interviewer_name=f"Step 3 - {interviewer.get_full_name() if interviewer else 'Interviewer'}"
    )
    flash('Đã gửi lại thư mời Step 3.' if ok else 'Gửi email thất bại, kiểm tra SMTP.', 'success' if ok else 'warning')
    return redirect(url_for('hr.candidate_management'))

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


@hr_bp.route('/candidates/<int:candidate_id>/link/step1', methods=['POST'])
@login_required
@hr_required
@audit_action('generate_step1_link')
def generate_step1_link(candidate_id: int):
    """Regenerate credentials and email Step1 link to candidate."""
    candidate = Candidate.query.get_or_404(candidate_id)
    expiry_days = current_app.config.get('LINK_EXPIRATION_DAYS', {}).get('step1_default', 7)
    username, password = create_candidate_credentials(candidate, expiry_days=expiry_days)
    login_url = url_for('candidate_auth.candidate_login', _external=True)
    body = (
        f"Xin chào {candidate.get_full_name()},\n\n"
        f"Tài khoản làm bài Step 1 của bạn:\n- Username: {username}\n- Password: {password}\n\n"
        f"Đường dẫn: {login_url}\nHạn sử dụng: {expiry_days} ngày.\n\nTrân trọng."
    )
    ok = send_email(candidate.email, 'Thông tin làm bài Step 1', body)
    flash('Đã tạo lại thông tin và gửi email.' if ok else 'Đã tạo thông tin; gửi email thất bại (kiểm tra SMTP).', 'success' if ok else 'warning')
    return redirect(url_for('hr.candidate_management'))

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
    """Danh sách vị trí với filter và phân trang."""
    # Filters
    department = request.args.get('department', '')
    level = request.args.get('level', '')
    active = request.args.get('active', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Position.query
    if department:
        query = query.filter_by(department=department)
    if level:
        query = query.filter_by(level=level)
    if active:
        query = query.filter_by(is_active=(active == 'true'))

    pagination = query.order_by(Position.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Choose options from config if available
    pm = current_app.config.get('POSITION_MANAGEMENT', {})
    departments = pm.get('departments', ['engineering', 'product', 'design', 'marketing'])
    levels = pm.get('levels', ['junior', 'mid', 'senior', 'lead'])

    return render_template('hr/positions.html',
                           positions=pagination,
                           departments=departments,
                           levels=levels,
                           filters={'department': department, 'level': level, 'active': active})


@hr_bp.route('/positions/create', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('create_position')
def create_position():
    """Tạo vị trí mới."""
    form = PositionForm()
    pm = current_app.config.get('POSITION_MANAGEMENT', {})
    form.department.choices = [(d, d.title()) for d in pm.get('departments', ['engineering', 'product', 'design', 'marketing'])]
    form.level.choices = [(l, l.title()) for l in pm.get('levels', ['junior', 'mid', 'senior', 'lead'])]
    if form.validate_on_submit():
        position = Position(
            title=form.title.data.strip(),
            department=form.department.data,
            level=form.level.data,
            salary_min=form.salary_min.data,
            salary_max=form.salary_max.data,
            description=form.description.data,
            required_skills=form.required_skills.data,
            target_start_date=form.target_start_date.data,
            hiring_urgency=form.hiring_urgency.data or 3,
            is_active=form.is_active.data,
            created_by=current_user.id,
        )
        db.session.add(position)
        db.session.commit()
        flash('Đã tạo vị trí mới.', 'success')
        return redirect(url_for('hr.position_management'))
    return render_template('hr/position_form.html', form=form, mode='create')


@hr_bp.route('/positions/<int:position_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_required
@audit_action('edit_position')
def edit_position(position_id: int):
    """Chỉnh sửa vị trí."""
    position = Position.query.get_or_404(position_id)
    form = PositionForm(obj=position)
    pm = current_app.config.get('POSITION_MANAGEMENT', {})
    form.department.choices = [(d, d.title()) for d in pm.get('departments', ['engineering', 'product', 'design', 'marketing'])]
    form.level.choices = [(l, l.title()) for l in pm.get('levels', ['junior', 'mid', 'senior', 'lead'])]
    if form.validate_on_submit():
        position.title = form.title.data.strip()
        position.department = form.department.data
        position.level = form.level.data
        position.salary_min = form.salary_min.data
        position.salary_max = form.salary_max.data
        position.description = form.description.data
        position.required_skills = form.required_skills.data
        position.target_start_date = form.target_start_date.data
        position.hiring_urgency = form.hiring_urgency.data or 3
        position.is_active = form.is_active.data
        db.session.commit()
        flash('Đã cập nhật vị trí.', 'success')
        return redirect(url_for('hr.position_management'))
    return render_template('hr/position_form.html', form=form, mode='edit', position=position)


@hr_bp.route('/positions/<int:position_id>/toggle', methods=['POST'])
@login_required
@hr_required
@audit_action('toggle_position')
def toggle_position(position_id: int):
    position = Position.query.get_or_404(position_id)
    position.is_active = not position.is_active
    db.session.commit()
    flash('Đã thay đổi trạng thái vị trí.', 'success')
    return redirect(url_for('hr.position_management'))

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