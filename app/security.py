"""
Security module for Mekong Recruitment System.

Implements rate limiting, comprehensive audit logging, and security utilities
following AGENT_RULES_DEVELOPER security requirements.
"""

import time
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from functools import wraps
from flask import request, g, current_app, session
from flask_login import current_user
from werkzeug.exceptions import TooManyRequests
import redis
from app.models import AuditLog, User, db


class RateLimiter:
    """
    Rate limiting implementation using Redis.
    
    Provides per-user and per-IP rate limiting with configurable
    windows and limits for different endpoints.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_limits = {
            'login': {'requests': 5, 'window': 300},  # 5 attempts per 5 minutes
            'assessment': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'api': {'requests': 1000, 'window': 3600},  # 1000 requests per hour
            'upload': {'requests': 10, 'window': 3600},  # 10 uploads per hour
            'export': {'requests': 20, 'window': 3600},  # 20 exports per hour
        }
    
    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"rate_limit:{endpoint}:{identifier}"
    
    def _get_identifier(self) -> str:
        """Get rate limiting identifier (user ID or IP)."""
        if current_user.is_authenticated:
            return f"user:{current_user.id}"
        return f"ip:{request.remote_addr}"
    
    def check_rate_limit(self, endpoint: str, custom_limits: Optional[Dict] = None) -> bool:
        """
        Check if request is within rate limits.
        
        Args:
            endpoint: Endpoint name for rate limiting
            custom_limits: Optional custom limits override
            
        Returns:
            True if within limits, False if exceeded
        """
        limits = custom_limits or self.default_limits.get(endpoint, self.default_limits['api'])
        identifier = self._get_identifier()
        key = self._get_key(identifier, endpoint)
        
        current_time = int(time.time())
        window_start = current_time - limits['window']
        
        # Get current requests in window
        try:
            requests = self.redis.zrangebyscore(key, window_start, '+inf')
            if len(requests) >= limits['requests']:
                return False
            
            # Add current request
            self.redis.zadd(key, {str(current_time): current_time})
            self.redis.expire(key, limits['window'])
            return True
            
        except redis.RedisError:
            # If Redis is unavailable, allow request but log warning
            current_app.logger.warning(f"Redis unavailable for rate limiting on {endpoint}")
            return True
    
    def get_remaining_requests(self, endpoint: str) -> int:
        """Get remaining requests for current user/IP."""
        limits = self.default_limits.get(endpoint, self.default_limits['api'])
        identifier = self._get_identifier()
        key = self._get_key(identifier, endpoint)
        
        current_time = int(time.time())
        window_start = current_time - limits['window']
        
        try:
            requests = self.redis.zrangebyscore(key, window_start, '+inf')
            return max(0, limits['requests'] - len(requests))
        except redis.RedisError:
            return limits['requests']


class AuditLogger:
    """
    Comprehensive audit logging system.
    
    Logs all security-relevant actions with detailed context,
    IP tracking, and user session information.
    """
    
    def __init__(self):
        self.sensitive_actions = {
            'user_login', 'user_logout', 'password_change', 'password_reset',
            'candidate_create', 'candidate_update', 'candidate_delete',
            'assessment_start', 'assessment_submit', 'assessment_score',
            'interview_schedule', 'interview_evaluate', 'interview_decision',
            'executive_decision', 'compensation_approval', 'file_upload',
            'data_export', 'admin_action', 'permission_change'
        }
    
    def log_action(self, action: str, details: Dict[str, Any], 
                   user_id: Optional[int] = None, 
                   severity: str = 'INFO') -> None:
        """
        Log security-relevant action with comprehensive details.
        
        Args:
            action: Action being performed
            details: Detailed context about the action
            user_id: ID of user performing action
            severity: Log severity level
        """
        try:
            # Get user information
            if user_id is None and current_user.is_authenticated:
                user_id = current_user.id
            
            # Collect request information
            request_info = {
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'referrer': request.headers.get('Referer', ''),
                'method': request.method,
                'endpoint': request.endpoint,
                'url': request.url,
                'session_id': session.get('_id', ''),
            }
            
            # Create audit log entry
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                details=json.dumps(details, default=str),
                ip_address=request_info['ip_address'],
                user_agent=request_info['user_agent'],
                severity=severity,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
            # Log to application logger for monitoring
            current_app.logger.info(
                f"AUDIT: {action} by user {user_id} from {request_info['ip_address']} - {severity}"
            )
            
        except Exception as e:
            current_app.logger.error(f"Failed to log audit action: {e}")
    
    def log_login_attempt(self, username: str, success: bool, 
                         user_id: Optional[int] = None) -> None:
        """Log login attempt with success/failure status."""
        details = {
            'username': username,
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        action = 'user_login_success' if success else 'user_login_failed'
        severity = 'INFO' if success else 'WARNING'
        
        self.log_action(action, details, user_id, severity)
    
    def log_assessment_action(self, candidate_id: int, action: str, 
                             details: Dict[str, Any]) -> None:
        """Log assessment-related actions."""
        full_details = {
            'candidate_id': candidate_id,
            'assessment_action': action,
            **details
        }
        
        self.log_action(f'assessment_{action}', full_details)
    
    def log_interview_action(self, candidate_id: int, interviewer_id: int,
                           action: str, details: Dict[str, Any]) -> None:
        """Log interview-related actions."""
        full_details = {
            'candidate_id': candidate_id,
            'interviewer_id': interviewer_id,
            'interview_action': action,
            **details
        }
        
        self.log_action(f'interview_{action}', full_details, interviewer_id)
    
    def log_executive_action(self, candidate_id: int, executive_id: int,
                           action: str, details: Dict[str, Any]) -> None:
        """Log executive decision actions."""
        full_details = {
            'candidate_id': candidate_id,
            'executive_id': executive_id,
            'executive_action': action,
            **details
        }
        
        self.log_action(f'executive_{action}', full_details, executive_id)
    
    def log_file_upload(self, filename: str, file_size: int, 
                       file_type: str, user_id: int) -> None:
        """Log file upload actions."""
        details = {
            'filename': filename,
            'file_size': file_size,
            'file_type': file_type,
            'upload_timestamp': datetime.utcnow().isoformat()
        }
        
        self.log_action('file_upload', details, user_id)
    
    def log_data_export(self, export_type: str, record_count: int,
                       user_id: int, filters: Optional[Dict] = None) -> None:
        """Log data export actions."""
        details = {
            'export_type': export_type,
            'record_count': record_count,
            'filters': filters or {},
            'export_timestamp': datetime.utcnow().isoformat()
        }
        
        self.log_action('data_export', details, user_id)


class SecurityUtils:
    """
    Security utility functions for input validation, sanitization,
    and security checks.
    """
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input to prevent XSS attacks."""
        if not text:
            return text
        
        # Basic HTML tag removal
        import re
        text = re.sub(r'<[^>]*>', '', text)
        
        # Remove potentially dangerous characters
        text = text.replace('javascript:', '')
        text = text.replace('onclick', '')
        text = text.replace('onload', '')
        text = text.replace('onerror', '')
        
        return text.strip()
    
    @staticmethod
    def validate_file_upload(filename: str, allowed_extensions: List[str],
                           max_size: int) -> Tuple[bool, str]:
        """
        Validate file upload for security.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return False, "No filename provided"
        
        # Check file extension
        import os
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            return False, f"File type {file_ext} not allowed"
        
        # Check file size
        if request.content_length and request.content_length > max_size:
            return False, f"File size exceeds maximum of {max_size} bytes"
        
        return True, ""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure token."""
        import secrets
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """Hash sensitive data for storage."""
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def check_suspicious_activity(user_id: int, action: str, 
                                time_window: int = 3600) -> bool:
        """
        Check for suspicious activity patterns.
        
        Args:
            user_id: User ID to check
            action: Action being performed
            time_window: Time window in seconds
            
        Returns:
            True if suspicious activity detected
        """
        try:
            # Count recent actions of same type
            recent_actions = AuditLog.query.filter(
                AuditLog.user_id == user_id,
                AuditLog.action == action,
                AuditLog.timestamp >= datetime.utcnow() - timedelta(seconds=time_window)
            ).count()
            
            # Define thresholds for different actions
            thresholds = {
                'user_login_failed': 5,
                'file_upload': 20,
                'data_export': 10,
                'assessment_submit': 3,
                'interview_evaluate': 10
            }
            
            threshold = thresholds.get(action, 50)
            return recent_actions > threshold
            
        except Exception as e:
            current_app.logger.error(f"Error checking suspicious activity: {e}")
            return False


# Global instances
rate_limiter = None
audit_logger = None
security_utils = SecurityUtils()


def init_security(redis_client: redis.Redis):
    """Initialize security components."""
    global rate_limiter, audit_logger
    rate_limiter = RateLimiter(redis_client)
    audit_logger = AuditLogger()


def rate_limit(endpoint: str, custom_limits: Optional[Dict] = None):
    """
    Decorator for rate limiting routes.
    
    Usage:
        @app.route('/api/data')
        @rate_limit('api')
        def get_data():
            return jsonify(data)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if rate_limiter is None:
                return f(*args, **kwargs)
            
            if not rate_limiter.check_rate_limit(endpoint, custom_limits):
                raise TooManyRequests("Rate limit exceeded")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def audit_log(action: str, severity: str = 'INFO'):
    """
    Decorator for automatic audit logging.
    
    Usage:
        @app.route('/candidates/create', methods=['POST'])
        @audit_log('candidate_create')
        def create_candidate():
            # Function implementation
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                
                # Log successful action
                if audit_logger:
                    details = {
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'status': 'success',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    audit_logger.log_action(action, details)
                
                return result
                
            except Exception as e:
                # Log failed action
                if audit_logger:
                    details = {
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'status': 'failed',
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    audit_logger.log_action(f"{action}_failed", details, severity='ERROR')
                
                raise
                
        return decorated_function
    return decorator


def security_check(f):
    """
    Decorator for comprehensive security checks.
    
    Performs input validation, suspicious activity detection,
    and security logging.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Input validation
        for key, value in request.args.items():
            if isinstance(value, str):
                request.args[key] = security_utils.sanitize_input(value)
        
        for key, value in request.form.items():
            if isinstance(value, str):
                request.form[key] = security_utils.sanitize_input(value)
        
        # Check for suspicious activity
        if current_user.is_authenticated:
            if security_utils.check_suspicious_activity(
                current_user.id, 
                f"{request.endpoint}_{request.method}"
            ):
                current_app.logger.warning(
                    f"Suspicious activity detected for user {current_user.id}"
                )
                # Could implement additional security measures here
        
        return f(*args, **kwargs)
    return decorated_function 