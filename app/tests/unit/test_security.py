"""
Unit tests for security module.

Tests rate limiting, audit logging, and security utilities
following AGENT_RULES_DEVELOPER testing requirements.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, request
from flask_login import current_user

from app.security import (
    RateLimiter, AuditLogger, SecurityUtils,
    rate_limit, audit_log, security_check
)


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_redis = Mock()
        self.rate_limiter = RateLimiter(self.mock_redis)
    
    def test_get_identifier_user_authenticated(self):
        """Test identifier generation for authenticated user."""
        with patch('app.security.current_user') as mock_user:
            mock_user.is_authenticated = True
            mock_user.id = 123
            
            with patch('app.security.request') as mock_request:
                mock_request.remote_addr = '192.168.1.1'
                
                identifier = self.rate_limiter._get_identifier()
                assert identifier == 'user:123'
    
    def test_get_identifier_ip_fallback(self):
        """Test identifier generation for unauthenticated user."""
        with patch('app.security.current_user') as mock_user:
            mock_user.is_authenticated = False
            
            with patch('app.security.request') as mock_request:
                mock_request.remote_addr = '192.168.1.1'
                
                identifier = self.rate_limiter._get_identifier()
                assert identifier == 'ip:192.168.1.1'
    
    def test_check_rate_limit_within_limits(self):
        """Test rate limit check when within limits."""
        self.mock_redis.zrangebyscore.return_value = ['1', '2', '3']  # 3 requests
        self.mock_redis.zadd.return_value = 1
        self.mock_redis.expire.return_value = True
        
        result = self.rate_limiter.check_rate_limit('api')
        assert result is True
        
        # Verify Redis calls
        self.mock_redis.zrangebyscore.assert_called_once()
        self.mock_redis.zadd.assert_called_once()
        self.mock_redis.expire.assert_called_once()
    
    def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limits exceeded."""
        # Simulate 1000 requests (exceeds default API limit)
        self.mock_redis.zrangebyscore.return_value = ['1'] * 1000
        
        result = self.rate_limiter.check_rate_limit('api')
        assert result is False
        
        # Should not add new request
        self.mock_redis.zadd.assert_not_called()
    
    def test_check_rate_limit_redis_error(self):
        """Test rate limit behavior when Redis is unavailable."""
        self.mock_redis.zrangebyscore.side_effect = Exception("Redis error")
        
        result = self.rate_limiter.check_rate_limit('api')
        assert result is True  # Should allow request when Redis fails
    
    def test_get_remaining_requests(self):
        """Test remaining requests calculation."""
        self.mock_redis.zrangebyscore.return_value = ['1', '2', '3']  # 3 requests
        
        remaining = self.rate_limiter.get_remaining_requests('api')
        # Default API limit is 1000, so remaining should be 997
        assert remaining == 997
    
    def test_custom_limits(self):
        """Test custom rate limits."""
        custom_limits = {'requests': 10, 'window': 3600}
        
        self.mock_redis.zrangebyscore.return_value = ['1', '2']  # 2 requests
        self.mock_redis.zadd.return_value = 1
        self.mock_redis.expire.return_value = True
        
        result = self.rate_limiter.check_rate_limit('custom', custom_limits)
        assert result is True


class TestAuditLogger:
    """Test audit logging functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.audit_logger = AuditLogger()
        self.mock_db = Mock()
        self.mock_audit_log = Mock()
    
    @patch('app.security.db')
    @patch('app.security.current_user')
    @patch('app.security.request')
    @patch('app.security.session')
    def test_log_action_success(self, mock_session, mock_request, mock_user, mock_db):
        """Test successful action logging."""
        # Mock current user
        mock_user.is_authenticated = True
        mock_user.id = 123
        
        # Mock request
        mock_request.remote_addr = '192.168.1.1'
        mock_request.headers.get.side_effect = lambda key, default='': {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'http://example.com'
        }.get(key, default)
        mock_request.method = 'POST'
        mock_request.endpoint = 'test_endpoint'
        mock_request.url = 'http://example.com/test'
        
        # Mock session
        mock_session.get.return_value = 'session_123'
        
        # Mock database
        mock_db.session.add.return_value = None
        mock_db.session.commit.return_value = None
        
        # Test logging
        details = {'test': 'data'}
        self.audit_logger.log_action('test_action', details, user_id=123)
        
        # Verify database calls
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()
    
    @patch('app.security.current_app')
    def test_log_action_exception(self, mock_app):
        """Test audit logging when database fails."""
        mock_app.logger.error = Mock()
        
        # Mock database to raise exception
        with patch('app.security.db') as mock_db:
            mock_db.session.add.side_effect = Exception("Database error")
            
            details = {'test': 'data'}
            self.audit_logger.log_action('test_action', details)
            
            # Should log error
            mock_app.logger.error.assert_called_once()
    
    def test_log_login_attempt_success(self):
        """Test login attempt logging for successful login."""
        with patch.object(self.audit_logger, 'log_action') as mock_log:
            self.audit_logger.log_login_attempt('testuser', True, 123)
            
            mock_log.assert_called_once_with(
                'user_login_success',
                {'username': 'testuser', 'success': True, 'timestamp': pytest.approx(datetime.utcnow(), abs=1)},
                123,
                'INFO'
            )
    
    def test_log_login_attempt_failure(self):
        """Test login attempt logging for failed login."""
        with patch.object(self.audit_logger, 'log_action') as mock_log:
            self.audit_logger.log_login_attempt('testuser', False, None)
            
            mock_log.assert_called_once_with(
                'user_login_failed',
                {'username': 'testuser', 'success': False, 'timestamp': pytest.approx(datetime.utcnow(), abs=1)},
                None,
                'WARNING'
            )
    
    def test_log_assessment_action(self):
        """Test assessment action logging."""
        with patch.object(self.audit_logger, 'log_action') as mock_log:
            details = {'score': 85, 'time_taken': 1800}
            self.audit_logger.log_assessment_action(456, 'submit', details)
            
            expected_details = {
                'candidate_id': 456,
                'assessment_action': 'submit',
                'score': 85,
                'time_taken': 1800
            }
            
            mock_log.assert_called_once_with('assessment_submit', expected_details)
    
    def test_log_interview_action(self):
        """Test interview action logging."""
        with patch.object(self.audit_logger, 'log_action') as mock_log:
            details = {'score': 8, 'notes': 'Good technical skills'}
            self.audit_logger.log_interview_action(456, 789, 'evaluate', details)
            
            expected_details = {
                'candidate_id': 456,
                'interviewer_id': 789,
                'interview_action': 'evaluate',
                'score': 8,
                'notes': 'Good technical skills'
            }
            
            mock_log.assert_called_once_with('interview_evaluate', expected_details, 789)
    
    def test_log_executive_action(self):
        """Test executive action logging."""
        with patch.object(self.audit_logger, 'log_action') as mock_log:
            details = {'decision': 'hire', 'compensation': 15000000}
            self.audit_logger.log_executive_action(456, 101, 'approve', details)
            
            expected_details = {
                'candidate_id': 456,
                'executive_id': 101,
                'executive_action': 'approve',
                'decision': 'hire',
                'compensation': 15000000
            }
            
            mock_log.assert_called_once_with('executive_approve', expected_details, 101)
    
    def test_log_file_upload(self):
        """Test file upload logging."""
        with patch.object(self.audit_logger, 'log_action') as mock_log:
            self.audit_logger.log_file_upload('resume.pdf', 1024000, 'pdf', 123)
            
            expected_details = {
                'filename': 'resume.pdf',
                'file_size': 1024000,
                'file_type': 'pdf',
                'upload_timestamp': pytest.approx(datetime.utcnow(), abs=1)
            }
            
            mock_log.assert_called_once_with('file_upload', expected_details, 123)
    
    def test_log_data_export(self):
        """Test data export logging."""
        with patch.object(self.audit_logger, 'log_action') as mock_log:
            filters = {'status': 'active', 'department': 'engineering'}
            self.audit_logger.log_data_export('candidates', 150, 123, filters)
            
            expected_details = {
                'export_type': 'candidates',
                'record_count': 150,
                'filters': filters,
                'export_timestamp': pytest.approx(datetime.utcnow(), abs=1)
            }
            
            mock_log.assert_called_once_with('data_export', expected_details, 123)


class TestSecurityUtils:
    """Test security utility functions."""
    
    def test_sanitize_input_normal(self):
        """Test input sanitization with normal text."""
        text = "Hello World"
        result = SecurityUtils.sanitize_input(text)
        assert result == "Hello World"
    
    def test_sanitize_input_html_tags(self):
        """Test input sanitization with HTML tags."""
        text = "<script>alert('xss')</script>Hello"
        result = SecurityUtils.sanitize_input(text)
        assert result == "Hello"
    
    def test_sanitize_input_javascript(self):
        """Test input sanitization with JavaScript."""
        text = "javascript:alert('xss')"
        result = SecurityUtils.sanitize_input(text)
        assert result == "alert('xss')"
    
    def test_sanitize_input_event_handlers(self):
        """Test input sanitization with event handlers."""
        text = "onclick=alert('xss') onload=alert('xss')"
        result = SecurityUtils.sanitize_input(text)
        assert result == "alert('xss') alert('xss')"
    
    def test_sanitize_input_empty(self):
        """Test input sanitization with empty input."""
        result = SecurityUtils.sanitize_input("")
        assert result == ""
    
    def test_sanitize_input_none(self):
        """Test input sanitization with None input."""
        result = SecurityUtils.sanitize_input(None)
        assert result is None
    
    @patch('app.security.request')
    def test_validate_file_upload_valid(self, mock_request):
        """Test file upload validation with valid file."""
        mock_request.content_length = 1024000  # 1MB
        
        is_valid, message = SecurityUtils.validate_file_upload(
            'test.pdf', ['.pdf', '.doc'], 5 * 1024 * 1024  # 5MB limit
        )
        
        assert is_valid is True
        assert message == ""
    
    @patch('app.security.request')
    def test_validate_file_upload_invalid_extension(self, mock_request):
        """Test file upload validation with invalid extension."""
        mock_request.content_length = 1024000
        
        is_valid, message = SecurityUtils.validate_file_upload(
            'test.exe', ['.pdf', '.doc'], 5 * 1024 * 1024
        )
        
        assert is_valid is False
        assert "File type .exe not allowed" in message
    
    @patch('app.security.request')
    def test_validate_file_upload_too_large(self, mock_request):
        """Test file upload validation with file too large."""
        mock_request.content_length = 10 * 1024 * 1024  # 10MB
        
        is_valid, message = SecurityUtils.validate_file_upload(
            'test.pdf', ['.pdf', '.doc'], 5 * 1024 * 1024  # 5MB limit
        )
        
        assert is_valid is False
        assert "File size exceeds maximum" in message
    
    def test_validate_file_upload_no_filename(self):
        """Test file upload validation with no filename."""
        is_valid, message = SecurityUtils.validate_file_upload(
            '', ['.pdf', '.doc'], 5 * 1024 * 1024
        )
        
        assert is_valid is False
        assert message == "No filename provided"
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token1 = SecurityUtils.generate_secure_token(32)
        token2 = SecurityUtils.generate_secure_token(32)
        
        assert len(token1) > 32
        assert len(token2) > 32
        assert token1 != token2  # Should be unique
    
    def test_hash_sensitive_data(self):
        """Test sensitive data hashing."""
        data = "sensitive_password"
        hash1 = SecurityUtils.hash_sensitive_data(data)
        hash2 = SecurityUtils.hash_sensitive_data(data)
        
        assert len(hash1) == 64  # SHA256 hex length
        assert hash1 == hash2  # Should be deterministic
    
    @patch('app.security.AuditLog')
    @patch('app.security.datetime')
    def test_check_suspicious_activity_normal(self, mock_datetime, mock_audit_log):
        """Test suspicious activity check with normal activity."""
        mock_datetime.utcnow.return_value = datetime(2023, 1, 1, 12, 0, 0)
        mock_audit_log.query.filter.return_value.count.return_value = 2
        
        result = SecurityUtils.check_suspicious_activity(123, 'user_login_failed')
        assert result is False  # 2 attempts < 5 threshold
    
    @patch('app.security.AuditLog')
    @patch('app.security.datetime')
    def test_check_suspicious_activity_suspicious(self, mock_datetime, mock_audit_log):
        """Test suspicious activity check with suspicious activity."""
        mock_datetime.utcnow.return_value = datetime(2023, 1, 1, 12, 0, 0)
        mock_audit_log.query.filter.return_value.count.return_value = 10
        
        result = SecurityUtils.check_suspicious_activity(123, 'user_login_failed')
        assert result is True  # 10 attempts > 5 threshold
    
    @patch('app.security.current_app')
    def test_check_suspicious_activity_exception(self, mock_app):
        """Test suspicious activity check when database fails."""
        mock_app.logger.error = Mock()
        
        with patch('app.security.AuditLog') as mock_audit_log:
            mock_audit_log.query.filter.side_effect = Exception("Database error")
            
            result = SecurityUtils.check_suspicious_activity(123, 'user_login_failed')
            assert result is False  # Should return False on error
            mock_app.logger.error.assert_called_once()


class TestSecurityDecorators:
    """Test security decorators."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    @patch('app.security.rate_limiter')
    def test_rate_limit_decorator_success(self, mock_rate_limiter):
        """Test rate limit decorator when within limits."""
        mock_rate_limiter.check_rate_limit.return_value = True
        
        @rate_limit('api')
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
        mock_rate_limiter.check_rate_limit.assert_called_once_with('api', None)
    
    @patch('app.security.rate_limiter')
    def test_rate_limit_decorator_exceeded(self, mock_rate_limiter):
        """Test rate limit decorator when limits exceeded."""
        mock_rate_limiter.check_rate_limit.return_value = False
        
        @rate_limit('api')
        def test_function():
            return "success"
        
        with pytest.raises(Exception):  # Should raise TooManyRequests
            test_function()
    
    @patch('app.security.audit_logger')
    def test_audit_log_decorator_success(self, mock_audit_logger):
        """Test audit log decorator for successful action."""
        mock_audit_logger.log_action = Mock()
        
        @audit_log('test_action')
        def test_function():
            return "success"
        
        with self.app.test_request_context('/test'):
            result = test_function()
        
        assert result == "success"
        mock_audit_logger.log_action.assert_called_once()
    
    @patch('app.security.audit_logger')
    def test_audit_log_decorator_failure(self, mock_audit_logger):
        """Test audit log decorator for failed action."""
        mock_audit_logger.log_action = Mock()
        
        @audit_log('test_action')
        def test_function():
            raise ValueError("Test error")
        
        with self.app.test_request_context('/test'):
            with pytest.raises(ValueError):
                test_function()
        
        # Should log both success and failure attempts
        assert mock_audit_logger.log_action.call_count >= 1
    
    @patch('app.security.security_utils')
    def test_security_check_decorator(self, mock_security_utils):
        """Test security check decorator."""
        mock_security_utils.sanitize_input.return_value = "sanitized"
        
        @security_check
        def test_function():
            return "success"
        
        with self.app.test_request_context('/test'):
            result = test_function()
        
        assert result == "success"
        # Should call sanitize_input for request parameters
        mock_security_utils.sanitize_input.assert_called()


if __name__ == '__main__':
    pytest.main([__file__]) 