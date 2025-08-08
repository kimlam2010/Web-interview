"""
Admin Blueprint for Mekong Recruitment System

This module provides admin functionality following AGENT_RULES_DEVELOPER:
- User management
- System configuration
- Question bank management
- System analytics
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo

from . import db
from .models import User

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

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            (User.username.ilike(like)) | (User.email.ilike(like)) | (User.first_name.ilike(like)) | (User.last_name.ilike(like))
        )
    if role:
        query = query.filter_by(role=role)

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=pagination.items, pagination=pagination, q=q, role=role)

@admin_bp.route('/questions')
@login_required
@admin_required
@audit_action('view_questions_management')
def questions():
    """
    Question bank management page.
    """
    return render_template('admin/questions.html')

@admin_bp.route('/system')
@login_required
@admin_required
@audit_action('view_system_config')
def system_config():
    """
    System configuration page.
    """
    return render_template('admin/system.html')

@admin_bp.route('/audit-logs')
@login_required
@admin_required
@audit_action('view_audit_logs')
def audit_logs():
    """
    Audit logs page.
    """
    return render_template('admin/audit_logs.html') 


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