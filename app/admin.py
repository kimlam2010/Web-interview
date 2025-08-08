"""
Admin Blueprint for Mekong Recruitment System

This module provides admin functionality following AGENT_RULES_DEVELOPER:
- User management
- System configuration
- Question bank management
- System analytics
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo, NumberRange
import json
import os

from . import db
from .models import User
from .models import AuditLog

from .decorators import admin_required, audit_action

# Create blueprint
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@login_required
@admin_required
@audit_action('view_admin_dashboard')
def admin_dashboard():
    """
    Admin dashboard.
    """
    return render_template('admin/dashboard.html')

@admin_bp.route('/users')
@login_required
@admin_required
@audit_action('view_users_management')
def users():
    """Danh sách người dùng với phân trang và tìm kiếm."""
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '', type=str)
    role = request.args.get('role', '', type=str)
    status = request.args.get('status', '', type=str)  # active, locked
    sort = request.args.get('sort', 'created_desc', type=str)

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            (User.username.ilike(like)) | (User.email.ilike(like)) | (User.first_name.ilike(like)) | (User.last_name.ilike(like))
        )
    if role:
        query = query.filter_by(role=role)
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'locked':
        query = query.filter_by(is_active=False)

    # Sorting options
    if sort == 'name_asc':
        query = query.order_by(User.last_name.asc(), User.first_name.asc())
    elif sort == 'name_desc':
        query = query.order_by(User.last_name.desc(), User.first_name.desc())
    elif sort == 'created_asc':
        query = query.order_by(User.created_at.asc())
    else:
        query = query.order_by(User.created_at.desc())

    pagination = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=pagination.items, pagination=pagination, q=q, role=role, status=status, sort=sort)

@admin_bp.route('/questions')
@login_required
@admin_required
@audit_action('view_questions_management')
def questions():
    """
    Question bank management page.
    """
    return render_template('admin/questions.html')

@admin_bp.route('/system', methods=['GET', 'POST'])
@login_required
@admin_required
@audit_action('view_system_config')
def system_config():
    """System configuration page with runtime overrides and persistence to instance/system_config.json."""
    class SystemConfigForm(FlaskForm):
        company_name = StringField('Tên công ty', validators=[DataRequired(), Length(max=100)])
        company_logo = StringField('Logo URL', validators=[Optional(), Length(max=255)])
        session_timeout_hours = IntegerField('Session timeout (giờ)', validators=[NumberRange(min=1, max=72)], default=4)
        token_length = IntegerField('Độ dài token link', validators=[NumberRange(min=12, max=64)], default=32)
        step1_link_exp_days = IntegerField('Hạn link Step1 (ngày)', validators=[NumberRange(min=1, max=30)], default=7)
        step2_link_exp_days = IntegerField('Hạn link Step2 (ngày)', validators=[NumberRange(min=1, max=30)], default=7)
        step3_link_exp_days = IntegerField('Hạn link Step3 (ngày)', validators=[NumberRange(min=1, max=30)], default=7)
        weekend_auto_extend = BooleanField('Tự động gia hạn nếu hết hạn vào cuối tuần')
        cors_allowed_origins = StringField('CORS allowed origins (CSV)', validators=[Optional(), Length(max=500)])
        enable_candidate_signup = BooleanField('Cho phép đăng ký ứng viên')
        # SMTP
        smtp_host = StringField('SMTP host', validators=[Optional(), Length(max=255)])
        smtp_port = IntegerField('SMTP port', validators=[Optional(), NumberRange(min=1, max=65535)])
        smtp_user = StringField('SMTP user', validators=[Optional(), Length(max=255)])
        smtp_pass = PasswordField('SMTP password', validators=[Optional(), Length(max=255)])
        smtp_tls = BooleanField('Use TLS/SSL')
        smtp_sender = StringField('Sender email', validators=[Optional(), Email()])
        test_email_to = StringField('Gửi email thử tới', validators=[Optional(), Email()])
        include_lowercase = BooleanField('Mật khẩu: chữ thường', default=True)
        include_uppercase = BooleanField('Mật khẩu: chữ hoa', default=True)
        include_numbers = BooleanField('Mật khẩu: số', default=True)
        include_special = BooleanField('Mật khẩu: ký tự đặc biệt', default=False)
        submit = SubmitField('Lưu cấu hình')

    # Load current values from app.config
    form = SystemConfigForm()
    if request.method == 'GET':
        form.company_name.data = current_app.config.get('COMPANY_NAME', 'Mekong Technology')
        form.company_logo.data = current_app.config.get('COMPANY_LOGO', 'static/img/mekong_logo.png')
        form.session_timeout_hours.data = int(current_app.permanent_session_lifetime.total_seconds() // 3600) if getattr(current_app, 'permanent_session_lifetime', None) else 4
        form.token_length.data = current_app.config.get('LINK_SECURITY', {}).get('token_length', 32)
        form.step1_link_exp_days.data = current_app.config.get('LINK_EXPIRATION_DAYS', {}).get('step1_default', 7)
        form.step2_link_exp_days.data = current_app.config.get('LINK_EXPIRATION_DAYS', {}).get('step2_default', 7)
        form.step3_link_exp_days.data = current_app.config.get('LINK_EXPIRATION_DAYS', {}).get('step3_default', 7)
        sp = current_app.config.get('SECURITY_POLICY', {})
        form.cors_allowed_origins.data = ','.join(sp.get('cors_allowed_origins', []) or [])
        form.enable_candidate_signup.data = bool(sp.get('enable_candidate_signup', False))
        pwc = current_app.config.get('CANDIDATE_CREDENTIALS', {}).get('password_complexity', {})
        form.include_lowercase.data = pwc.get('include_lowercase', True)
        form.include_uppercase.data = pwc.get('include_uppercase', True)
        form.include_numbers.data = pwc.get('include_numbers', True)
        form.include_special.data = pwc.get('include_special', False)
        form.weekend_auto_extend.data = current_app.config.get('REMINDER_SCHEDULE', {}).get('weekend_auto_extend', False)
        # SMTP
        email_cfg = current_app.config.get('EMAIL_CONFIG', {})
        form.smtp_host.data = email_cfg.get('host')
        form.smtp_port.data = email_cfg.get('port')
        form.smtp_user.data = email_cfg.get('username')
        form.smtp_sender.data = email_cfg.get('sender')

    # Reset to defaults
    if request.method == 'GET' and request.args.get('reset'):
        try:
            cfg_path = os.path.join(current_app.instance_path, 'system_config.json')
            if os.path.exists(cfg_path):
                os.remove(cfg_path)
            flash('Đã khôi phục cấu hình mặc định. Vui lòng khởi động lại ứng dụng nếu cần.', 'info')
            return redirect(url_for('admin.system_config'))
        except Exception as e:
            flash(f'Lỗi khôi phục mặc định: {e}', 'error')

    if form.validate_on_submit():
        # Update runtime config
        current_app.config['COMPANY_NAME'] = form.company_name.data
        current_app.config['COMPANY_LOGO'] = form.company_logo.data or 'static/img/mekong_logo.png'
        # Session lifetime
        from datetime import timedelta
        current_app.permanent_session_lifetime = timedelta(hours=form.session_timeout_hours.data)
        # Token/security
        link_sec = dict(current_app.config.get('LINK_SECURITY', {}))
        link_sec['token_length'] = form.token_length.data
        current_app.config['LINK_SECURITY'] = link_sec
        # Link expiration
        link_exp = dict(current_app.config.get('LINK_EXPIRATION_DAYS', {}))
        link_exp['step1_default'] = form.step1_link_exp_days.data
        link_exp['step2_default'] = form.step2_link_exp_days.data
        link_exp['step3_default'] = form.step3_link_exp_days.data
        current_app.config['LINK_EXPIRATION_DAYS'] = link_exp
        # Password complexity
        cand_cfg = dict(current_app.config.get('CANDIDATE_CREDENTIALS', {}))
        cand_cfg['password_complexity'] = {
            'include_lowercase': bool(form.include_lowercase.data),
            'include_uppercase': bool(form.include_uppercase.data),
            'include_numbers': bool(form.include_numbers.data),
            'include_special': bool(form.include_special.data),
            'exclude_ambiguous': True,
        }
        current_app.config['CANDIDATE_CREDENTIALS'] = cand_cfg
        # Reminder config
        reminder = dict(current_app.config.get('REMINDER_SCHEDULE', {}))
        reminder['weekend_auto_extend'] = bool(form.weekend_auto_extend.data)
        current_app.config['REMINDER_SCHEDULE'] = reminder

        # Security policy
        security_policy = dict(current_app.config.get('SECURITY_POLICY', {}))
        security_policy.setdefault('max_login_attempts', 3)
        security_policy.setdefault('lockout_minutes', 30)
        # CORS + signup
        cors_csv = (form.cors_allowed_origins.data or '').strip()
        security_policy['cors_allowed_origins'] = [s.strip() for s in cors_csv.split(',') if s.strip()] if cors_csv else []
        security_policy['enable_candidate_signup'] = bool(form.enable_candidate_signup.data)
        current_app.config['SECURITY_POLICY'] = security_policy

        # Email config
        email_cfg = {
            'host': form.smtp_host.data,
            'port': form.smtp_port.data,
            'username': form.smtp_user.data,
            'password': form.smtp_pass.data,
            'use_tls': bool(form.smtp_tls.data),
            'sender': form.smtp_sender.data,
        }
        current_app.config['EMAIL_CONFIG'] = email_cfg

        # Persist to instance/system_config.json
        data = {
            'COMPANY_NAME': current_app.config['COMPANY_NAME'],
            'COMPANY_LOGO': current_app.config['COMPANY_LOGO'],
            'SESSION_TIMEOUT_HOURS': form.session_timeout_hours.data,
            'LINK_SECURITY': current_app.config['LINK_SECURITY'],
            'LINK_EXPIRATION_DAYS': current_app.config['LINK_EXPIRATION_DAYS'],
            'CANDIDATE_CREDENTIALS': current_app.config['CANDIDATE_CREDENTIALS'],
            'REMINDER_SCHEDULE': current_app.config['REMINDER_SCHEDULE'],
            'SECURITY_POLICY': current_app.config['SECURITY_POLICY'],
            'EMAIL_CONFIG': current_app.config['EMAIL_CONFIG'],
        }
        instance_dir = current_app.instance_path
        os.makedirs(instance_dir, exist_ok=True)
        cfg_path = os.path.join(instance_dir, 'system_config.json')
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        flash('Đã lưu cấu hình hệ thống.', 'success')
        return redirect(url_for('admin.system_config'))

    return render_template('admin/system.html', form=form)


@admin_bp.route('/system/export')
@login_required
@admin_required
def export_system_config():
    from flask import send_file
    cfg_path = os.path.join(current_app.instance_path, 'system_config.json')
    if not os.path.exists(cfg_path):
        flash('Chưa có cấu hình để export.', 'warning')
        return redirect(url_for('admin.system_config'))
    return send_file(cfg_path, as_attachment=True, download_name='system_config.json')


@admin_bp.route('/system/import', methods=['POST'])
@login_required
@admin_required
def import_system_config():
    file = request.files.get('config_file')
    if not file or not file.filename.lower().endswith('.json'):
        flash('Vui lòng chọn file JSON hợp lệ.', 'error')
        return redirect(url_for('admin.system_config'))
    try:
        data = json.load(file)
        # Validate sơ bộ
        required_keys = ['COMPANY_NAME', 'LINK_SECURITY']
        for k in required_keys:
            if k not in data:
                raise ValueError(f'Thiếu khóa bắt buộc: {k}')
        os.makedirs(current_app.instance_path, exist_ok=True)
        cfg_path = os.path.join(current_app.instance_path, 'system_config.json')
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        flash('Đã import cấu hình. Vui lòng tải lại trang.', 'success')
    except Exception as e:
        flash(f'Lỗi import: {e}', 'error')
    return redirect(url_for('admin.system_config'))


@admin_bp.route('/system/history')
@login_required
@admin_required
def system_config_history():
    versions_dir = os.path.join(current_app.instance_path, 'config_versions')
    items = []
    if os.path.exists(versions_dir):
        for name in sorted(os.listdir(versions_dir), reverse=True):
            if name.endswith('.json'):
                items.append(name)
    return render_template('admin/system_history.html', items=items)


@admin_bp.route('/system/rollback/<path:filename>', methods=['POST'])
@login_required
@admin_required
def system_config_rollback(filename: str):
    versions_dir = os.path.join(current_app.instance_path, 'config_versions')
    src = os.path.join(versions_dir, filename)
    if not os.path.exists(src):
        flash('Phiên bản không tồn tại.', 'error')
        return redirect(url_for('admin.system_config_history'))
    dst = os.path.join(current_app.instance_path, 'system_config.json')
    try:
        with open(src, 'r', encoding='utf-8') as f:
            data = json.load(f)
        with open(dst, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        flash('Đã rollback cấu hình.', 'success')
    except Exception as e:
        flash(f'Rollback thất bại: {e}', 'error')
    return redirect(url_for('admin.system_config'))


@admin_bp.route('/system/token-sample')
@login_required
@admin_required
def token_sample():
    from app.utils import generate_assessment_token
    token = generate_assessment_token()
    return {'token': token}

@admin_bp.route('/audit-logs')
@login_required
@admin_required
@audit_action('view_audit_logs')
def audit_logs():
    """Audit logs page with filters and pagination."""
    page = request.args.get('page', 1, type=int)
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action', default='', type=str)
    date_from = request.args.get('from', default='', type=str)
    date_to = request.args.get('to', default='', type=str)

    query = AuditLog.query
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    from datetime import datetime
    fmt = '%Y-%m-%d'
    try:
        if date_from:
            query = query.filter(AuditLog.timestamp >= datetime.strptime(date_from, fmt))
        if date_to:
            query = query.filter(AuditLog.timestamp <= datetime.strptime(date_to, fmt))
    except ValueError:
        flash('Định dạng ngày không hợp lệ (YYYY-MM-DD).', 'error')

    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/audit_logs.html', logs=pagination.items, pagination=pagination, user_id=user_id, action=action, date_from=date_from, date_to=date_to)


@admin_bp.route('/system/test-email', methods=['POST'])
@login_required
@admin_required
def system_test_email():
    to_email = request.form.get('test_email_to')
    if not to_email:
        flash('Vui lòng nhập email nhận thử.', 'error')
        return redirect(url_for('admin.system_config'))
    from app.utils import send_email
    ok = send_email(to_email, 'Email thử nghiệm', 'Đây là email thử nghiệm từ hệ thống')
    flash('Đã gửi email thử.' if ok else 'Gửi email thử thất bại.', 'success' if ok else 'error')
    return redirect(url_for('admin.system_config'))


# =============== User Forms ===============
class UserCreateForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('First name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    role = SelectField('Role', choices=[('admin', 'admin'), ('hr', 'hr'), ('interviewer', 'interviewer'), ('executive', 'executive')], validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)], description='Tối thiểu 6 ký tự')
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Mật khẩu không khớp')])
    submit = SubmitField('Lưu')


class UserEditForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('First name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    role = SelectField('Role', choices=[('admin', 'admin'), ('hr', 'hr'), ('interviewer', 'interviewer'), ('executive', 'executive')], validators=[DataRequired()])
    is_active = BooleanField('Active')
    password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[Optional(), EqualTo('password', message='Mật khẩu không khớp')])
    submit = SubmitField('Cập nhật')


# =============== User CRUD Routes ===============
@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
@audit_action('create_user')
def create_user():
    form = UserCreateForm()
    if form.validate_on_submit():
        if User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first():
            flash('Username hoặc Email đã tồn tại.', 'error')
            return render_template('admin/user_form.html', form=form, mode='create')

        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role=form.role.data,
            is_active=form.is_active.data,
            password=form.password.data,
        )
        db.session.add(user)
        db.session.commit()
        flash('Tạo người dùng thành công.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, mode='create')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
@audit_action('edit_user')
def edit_user(user_id: int):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    if form.validate_on_submit():
        # Check email uniqueness if changed
        if user.email != form.email.data and User.query.filter_by(email=form.email.data).first():
            flash('Email đã được sử dụng.', 'error')
            return render_template('admin/user_form.html', form=form, mode='edit', user=user)

        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.phone = form.phone.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('Cập nhật người dùng thành công.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, mode='edit', user=user)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
@audit_action('toggle_user_active')
def toggle_user_active(user_id: int):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(('Đã mở khóa' if user.is_active else 'Đã khóa') + f' tài khoản {user.username}.', 'success')
    return redirect(url_for('admin.users', **request.args))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
@audit_action('reset_user_password')
def reset_user_password(user_id: int):
    import secrets
    user = User.query.get_or_404(user_id)
    temp_password = secrets.token_urlsafe(8)
    user.set_password(temp_password)
    db.session.commit()
    flash(f'Mật khẩu tạm thời của {user.username}: {temp_password}', 'info')
    return redirect(url_for('admin.users', **request.args))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
@audit_action('soft_delete_user')
def soft_delete_user(user_id: int):
    """Soft delete = vô hiệu hóa tài khoản (không xóa dữ liệu)."""
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    flash(f'Đã vô hiệu hóa tài khoản {user.username}.', 'success')
    return redirect(url_for('admin.users', **request.args))