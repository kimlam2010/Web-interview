"""
Permission Decorators for Role-Based Access Control

This module provides permission decorators following AGENT_RULES_DEVELOPER:
- Permission decorators cho route protection
- Role-based access control
- Audit logging cho user actions
- Comprehensive security validation
"""

from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user, login_required
from typing import Optional, Callable, Any
import logging

from .models import AuditLog
from app.utils import log_audit_event, get_client_ip

logger = logging.getLogger(__name__)

def permission_required(permission: str) -> Callable:
    """
    Decorator to check if user has specific permission.
    
    Args:
        permission (str): Permission name to check
        
    Returns:
        Callable: Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Admin luôn có toàn quyền
            if getattr(current_user, 'role', None) == 'admin':
                return f(*args, **kwargs)

            if not current_user.has_permission(permission):
                # Log unauthorized access attempt
                log_audit_event(
                    user_id=current_user.id,
                    action='unauthorized_access',
                    resource_type='route',
                    resource_id=None,
                    details={
                        'permission_required': permission,
                        'user_role': current_user.role,
                        'route': request.endpoint,
                        'ip_address': get_client_ip()
                    }
                )
                
                flash('Access denied. You do not have permission to access this resource.', 'error')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(role: str) -> Callable:
    """
    Decorator to check if user has specific role.
    
    Args:
        role (str): Role name to check
        
    Returns:
        Callable: Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Admin luôn có toàn quyền
            if current_user.role != role and current_user.role != 'admin':
                # Log unauthorized access attempt
                log_audit_event(
                    user_id=current_user.id,
                    action='unauthorized_access',
                    resource_type='route',
                    resource_id=None,
                    details={
                        'role_required': role,
                        'user_role': current_user.role,
                        'route': request.endpoint,
                        'ip_address': get_client_ip()
                    }
                )
                
                flash(f'Access denied. {role.title()} role required.', 'error')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f: Callable) -> Callable:
    """
    Decorator to require admin role.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return role_required('admin')(f)

def hr_required(f: Callable) -> Callable:
    """
    Decorator to require HR role.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return role_required('hr')(f)

def interviewer_required(f: Callable) -> Callable:
    """
    Decorator to require interviewer role.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return role_required('interviewer')(f)

def executive_required(f: Callable) -> Callable:
    """
    Decorator to require executive role.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    return role_required('executive')(f)

def audit_action(action: str, resource_type: str = None) -> Callable:
    """
    Decorator to automatically log audit events.
    
    Args:
        action (str): Action being performed
        resource_type (str): Type of resource being accessed
        
    Returns:
        Callable: Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            result = f(*args, **kwargs)
            
            # Log the action
            log_audit_event(
                user_id=current_user.id if current_user.is_authenticated else None,
                action=action,
                resource_type=resource_type or 'route',
                resource_id=kwargs.get('id'),
                details={
                    'route': request.endpoint,
                    'method': request.method,
                    'ip_address': get_client_ip(),
                    'user_agent': request.user_agent.string
                }
            )
            
            return result
        return decorated_function
    return decorator

def validate_resource_access(resource_type: str, resource_id_param: str = 'id') -> Callable:
    """
    Decorator to validate user access to specific resources.
    
    Args:
        resource_type (str): Type of resource to validate
        resource_id_param (str): Parameter name containing resource ID
        
    Returns:
        Callable: Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            resource_id = kwargs.get(resource_id_param)
            if not resource_id:
                abort(400, description="Resource ID not provided")
            
            # Admin luôn có toàn quyền
            if getattr(current_user, 'role', None) == 'admin':
                return f(*args, **kwargs)

            # Validate access based on resource type
            if resource_type == 'candidate':
                from .models import Candidate
                candidate = Candidate.query.get_or_404(resource_id)
                
                # HR can access all candidates, others need specific permissions
                if current_user.role == 'hr':
                    pass  # HR has access to all candidates
                elif current_user.role == 'interviewer':
                    # Interviewers can only access assigned candidates
                    if not candidate.interview_evaluations or not any(
                        eval.interviewer_id == current_user.id 
                        for eval in candidate.interview_evaluations
                    ):
                        flash('Access denied. You can only access assigned candidates.', 'error')
                        return redirect(url_for('main.dashboard'))
                else:
                    # Other roles need specific permissions
                    if not current_user.has_permission('view_all_candidates'):
                        flash('Access denied. You do not have permission to view candidates.', 'error')
                        return redirect(url_for('main.dashboard'))
            
            elif resource_type == 'user':
                from .models import User
                user = User.query.get_or_404(resource_id)
                
                # Users can only access their own profile unless admin
                if current_user.role != 'admin' and current_user.id != user.id:
                    flash('Access denied. You can only access your own profile.', 'error')
                    return redirect(url_for('main.dashboard'))
            
            elif resource_type == 'position':
                from .models import Position
                position = Position.query.get_or_404(resource_id)
                
                # Only HR and admin can access positions
                if current_user.role not in ['hr', 'admin']:
                    flash('Access denied. You do not have permission to access positions.', 'error')
                    return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit(max_requests: int = 100, window: int = 3600) -> Callable:
    """
    Basic rate limiting decorator.
    
    Args:
        max_requests (int): Maximum requests per window
        window (int): Time window in seconds
        
    Returns:
        Callable: Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # TODO: Implement proper rate limiting with Redis
            # For now, this is a placeholder
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_form_data(required_fields: list) -> Callable:
    """
    Decorator to validate form data.
    
    Args:
        required_fields (list): List of required field names
        
    Returns:
        Callable: Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if request.method == 'POST':
                missing_fields = []
                for field in required_fields:
                    if not request.form.get(field):
                        missing_fields.append(field)
                
                if missing_fields:
                    flash(f'Missing required fields: {", ".join(missing_fields)}', 'error')
                    return redirect(request.url)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def handle_errors(f: Callable) -> Callable:
    """
    Decorator to handle common errors gracefully.
    
    Args:
        f (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            
            # Log the error
            if current_user.is_authenticated:
                log_audit_event(
                    user_id=current_user.id,
                    action='error_occurred',
                    resource_type='route',
                    resource_id=None,
                    details={
                        'error': str(e),
                        'route': request.endpoint,
                        'method': request.method,
                        'ip_address': get_client_ip()
                    }
                )
            
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('main.dashboard'))
    
    return decorated_function

# Convenience decorators for common permissions
manage_questions_required = permission_required('manage_questions')
manage_users_required = permission_required('manage_users')
view_all_candidates_required = permission_required('view_all_candidates')
export_data_required = permission_required('export_data')
conduct_step3_required = permission_required('conduct_step3')
approve_final_hiring_required = permission_required('approve_final_hiring') 