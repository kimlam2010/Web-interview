"""
Error Handling & Monitoring Module

Comprehensive error handling and monitoring system with health check endpoints,
performance monitoring, automated error reporting, and system status dashboard.
"""

import traceback
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app, render_template
from sqlalchemy import text, func
from app.models import db, User, Candidate, AssessmentResult, InterviewEvaluation
from app.decorators import admin_required
from app.security import audit_log, rate_limit

error_monitoring_bp = Blueprint('error_monitoring', __name__)


class HealthCheckManager:
    """Health check system for monitoring application status."""
    
    @staticmethod
    def check_database_health() -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            
            # Test basic database connectivity
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            
            # Test complex query performance
            candidate_count = db.session.query(func.count(Candidate.id)).scalar()
            
            execution_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time': round(execution_time, 3),
                'candidate_count': candidate_count,
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    @staticmethod
    def check_redis_health() -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        try:
            start_time = time.time()
            
            if hasattr(current_app, 'redis_client'):
                # Test Redis connectivity
                current_app.redis_client.ping()
                
                # Test basic operations
                test_key = "health_check_test"
                current_app.redis_client.set(test_key, "test_value", ex=60)
                value = current_app.redis_client.get(test_key)
                current_app.redis_client.delete(test_key)
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'healthy',
                    'response_time': round(execution_time, 3),
                    'last_check': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'not_configured',
                    'message': 'Redis client not initialized',
                    'last_check': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    @staticmethod
    def check_file_system_health() -> Dict[str, Any]:
        """Check file system accessibility and disk space."""
        try:
            import os
            import shutil
            
            # Check if upload directory exists and is writable
            upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)
            
            # Test file write/read
            test_file = os.path.join(upload_dir, 'health_check.txt')
            with open(test_file, 'w') as f:
                f.write('health_check')
            
            with open(test_file, 'r') as f:
                content = f.read()
            
            os.remove(test_file)
            
            # Get disk usage
            total, used, free = shutil.disk_usage(upload_dir)
            disk_usage_percent = (used / total) * 100
            
            return {
                'status': 'healthy',
                'disk_usage_percent': round(disk_usage_percent, 2),
                'free_space_gb': round(free / (1024**3), 2),
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    @staticmethod
    def check_external_services() -> Dict[str, Any]:
        """Check external service dependencies."""
        services = {}
        
        # Check email service (if configured)
        try:
            smtp_host = current_app.config.get('MAIL_SERVER')
            if smtp_host:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((smtp_host, 587))
                sock.close()
                
                services['email'] = {
                    'status': 'healthy' if result == 0 else 'unhealthy',
                    'host': smtp_host,
                    'port': 587
                }
            else:
                services['email'] = {
                    'status': 'not_configured',
                    'message': 'SMTP not configured'
                }
        except Exception as e:
            services['email'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Check CDN service (if configured)
        try:
            cdn_url = current_app.config.get('CDN_BASE_URL')
            if cdn_url:
                import requests
                response = requests.get(cdn_url, timeout=5)
                services['cdn'] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'response_code': response.status_code
                }
            else:
                services['cdn'] = {
                    'status': 'not_configured',
                    'message': 'CDN not configured'
                }
        except Exception as e:
            services['cdn'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return services
    
    @staticmethod
    def comprehensive_health_check() -> Dict[str, Any]:
        """Perform comprehensive health check of all systems."""
        start_time = time.time()
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {
                'database': HealthCheckManager.check_database_health(),
                'redis': HealthCheckManager.check_redis_health(),
                'file_system': HealthCheckManager.check_file_system_health(),
                'external_services': HealthCheckManager.check_external_services()
            },
            'response_time': 0
        }
        
        # Determine overall status
        unhealthy_checks = []
        for service, status in health_report['checks'].items():
            if isinstance(status, dict) and status.get('status') == 'unhealthy':
                unhealthy_checks.append(service)
        
        if unhealthy_checks:
            health_report['overall_status'] = 'unhealthy'
            health_report['unhealthy_services'] = unhealthy_checks
        
        health_report['response_time'] = round(time.time() - start_time, 3)
        
        return health_report


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.metrics = {}
    
    def record_metric(self, metric_name: str, value: float, category: str = 'general'):
        """Record a performance metric."""
        if category not in self.metrics:
            self.metrics[category] = {}
        
        if metric_name not in self.metrics[category]:
            self.metrics[category][metric_name] = []
        
        self.metrics[category][metric_name].append({
            'value': value,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 1000 measurements
        if len(self.metrics[category][metric_name]) > 1000:
            self.metrics[category][metric_name] = self.metrics[category][metric_name][-1000:]
    
    def get_metric_average(self, metric_name: str, category: str = 'general', hours: int = 24) -> float:
        """Get average value for a metric over specified hours."""
        if category not in self.metrics or metric_name not in self.metrics[category]:
            return 0.0
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_values = [
            m['value'] for m in self.metrics[category][metric_name]
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]
        
        return sum(recent_values) / len(recent_values) if recent_values else 0.0
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all metrics."""
        summary = {}
        
        for category, metrics in self.metrics.items():
            summary[category] = {}
            for metric_name, measurements in metrics.items():
                if measurements:
                    values = [m['value'] for m in measurements[-100:]]  # Last 100 measurements
                    summary[category][metric_name] = {
                        'current': values[-1] if values else 0,
                        'average': sum(values) / len(values) if values else 0,
                        'min': min(values) if values else 0,
                        'max': max(values) if values else 0,
                        'count': len(values)
                    }
        
        return summary


class AutomatedErrorReporter:
    """Automated error reporting and alerting system."""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.error_queue = "error_reports"
        self.alert_threshold = 10  # Number of errors before alerting
    
    def report_error(self, error: Exception, context: Dict = None):
        """Report an error for monitoring and alerting."""
        error_report = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'request_info': {
                'url': request.url if request else None,
                'method': request.method if request else None,
                'user_agent': request.headers.get('User-Agent') if request else None,
                'ip_address': request.remote_addr if request else None
            }
        }
        
        # Store error report
        if self.redis:
            try:
                self.redis.lpush(self.error_queue, json.dumps(error_report))
                self.redis.ltrim(self.error_queue, 0, 999)  # Keep only last 1000 errors
            except Exception as e:
                current_app.logger.error(f"Failed to store error report: {e}")
        
        # Check if we need to send an alert
        self.check_alert_conditions()
        
        # Log error
        current_app.logger.error(f"Error reported: {error_report}")
    
    def check_alert_conditions(self):
        """Check if error conditions warrant an alert."""
        if not self.redis:
            return
        
        try:
            # Count recent errors (last hour)
            cutoff_time = datetime.now() - timedelta(hours=1)
            recent_errors = []
            
            # Get all error reports
            error_reports = self.redis.lrange(self.error_queue, 0, -1)
            
            for report_json in error_reports:
                try:
                    report = json.loads(report_json)
                    report_time = datetime.fromisoformat(report['timestamp'])
                    if report_time > cutoff_time:
                        recent_errors.append(report)
                except:
                    continue
            
            # Check if we have too many errors
            if len(recent_errors) >= self.alert_threshold:
                self.send_error_alert(recent_errors)
                
        except Exception as e:
            current_app.logger.error(f"Failed to check alert conditions: {e}")
    
    def send_error_alert(self, recent_errors: List[Dict]):
        """Send error alert to administrators."""
        alert_message = {
            'type': 'error_alert',
            'timestamp': datetime.now().isoformat(),
            'error_count': len(recent_errors),
            'time_period': '1 hour',
            'sample_errors': recent_errors[:5]  # Include first 5 errors as sample
        }
        
        # This would integrate with email/notification system
        current_app.logger.critical(f"ERROR ALERT: {alert_message}")
        
        # Store alert
        if self.redis:
            try:
                self.redis.lpush("error_alerts", json.dumps(alert_message))
            except Exception as e:
                current_app.logger.error(f"Failed to store error alert: {e}")
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for specified time period."""
        if not self.redis:
            return {'error': 'Redis not available'}
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            error_reports = []
            
            # Get all error reports
            all_reports = self.redis.lrange(self.error_queue, 0, -1)
            
            for report_json in all_reports:
                try:
                    report = json.loads(report_json)
                    report_time = datetime.fromisoformat(report['timestamp'])
                    if report_time > cutoff_time:
                        error_reports.append(report)
                except:
                    continue
            
            # Analyze errors
            error_types = {}
            for report in error_reports:
                error_type = report.get('error_type', 'Unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            return {
                'total_errors': len(error_reports),
                'error_types': error_types,
                'time_period_hours': hours,
                'recent_errors': error_reports[:10]  # Last 10 errors
            }
            
        except Exception as e:
            return {'error': str(e)}


class SystemStatusDashboard:
    """System status dashboard for monitoring."""
    
    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        """Get comprehensive system status."""
        status = {
            'timestamp': datetime.now().isoformat(),
            'uptime': SystemStatusDashboard.get_uptime(),
            'health': HealthCheckManager.comprehensive_health_check(),
            'performance': SystemStatusDashboard.get_performance_metrics(),
            'errors': SystemStatusDashboard.get_error_summary(),
            'database_stats': SystemStatusDashboard.get_database_stats(),
            'user_stats': SystemStatusDashboard.get_user_stats()
        }
        
        return status
    
    @staticmethod
    def get_uptime() -> Dict[str, Any]:
        """Get application uptime information."""
        # This would be more sophisticated in production
        # For now, we'll return basic information
        return {
            'start_time': current_app.config.get('APP_START_TIME', datetime.now().isoformat()),
            'uptime_seconds': int(time.time() - current_app.config.get('APP_START_TIMESTAMP', time.time())),
            'version': current_app.config.get('APP_VERSION', '1.0.0')
        }
    
    @staticmethod
    def get_performance_metrics() -> Dict[str, Any]:
        """Get current performance metrics."""
        if hasattr(current_app, 'performance_monitor'):
            return current_app.performance_monitor.get_performance_summary()
        else:
            return {'error': 'Performance monitor not initialized'}
    
    @staticmethod
    def get_error_summary() -> Dict[str, Any]:
        """Get error summary."""
        if hasattr(current_app, 'error_reporter'):
            return current_app.error_reporter.get_error_summary()
        else:
            return {'error': 'Error reporter not initialized'}
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = {
                'candidates': db.session.query(func.count(Candidate.id)).scalar(),
                'users': db.session.query(func.count(User.id)).scalar(),
                'assessment_results': db.session.query(func.count(AssessmentResult.id)).scalar(),
                'interview_evaluations': db.session.query(func.count(InterviewEvaluation.id)).scalar()
            }
            
            # Get recent activity
            recent_candidates = db.session.query(func.count(Candidate.id))\
                .filter(Candidate.created_at >= datetime.now() - timedelta(days=7))\
                .scalar()
            
            stats['recent_candidates_7d'] = recent_candidates
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_user_stats() -> Dict[str, Any]:
        """Get user activity statistics."""
        try:
            # Get user counts by role
            role_counts = db.session.query(
                User.role,
                func.count(User.id)
            ).group_by(User.role).all()
            
            stats = {
                'total_users': db.session.query(func.count(User.id)).scalar(),
                'role_distribution': dict(role_counts),
                'active_users_24h': 0,  # Would need user activity tracking
                'new_users_7d': db.session.query(func.count(User.id))\
                    .filter(User.created_at >= datetime.now() - timedelta(days=7))\
                    .scalar()
            }
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}


# Route Definitions

@error_monitoring_bp.route('/health')
@rate_limit('health', {'requests': 100, 'window': 3600})
def health_check():
    """Basic health check endpoint."""
    try:
        health_report = HealthCheckManager.comprehensive_health_check()
        status_code = 200 if health_report['overall_status'] == 'healthy' else 503
        
        return jsonify(health_report), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@error_monitoring_bp.route('/health/detailed')
@admin_required
@rate_limit('admin', {'requests': 20, 'window': 3600})
def detailed_health_check():
    """Detailed health check for administrators."""
    try:
        health_report = HealthCheckManager.comprehensive_health_check()
        
        # Add additional detailed information
        health_report['detailed'] = {
            'database': HealthCheckManager.check_database_health(),
            'redis': HealthCheckManager.check_redis_health(),
            'file_system': HealthCheckManager.check_file_system_health(),
            'external_services': HealthCheckManager.check_external_services()
        }
        
        return jsonify(health_report)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@error_monitoring_bp.route('/monitoring/dashboard')
@admin_required
@rate_limit('admin', {'requests': 10, 'window': 3600})
def monitoring_dashboard():
    """System monitoring dashboard."""
    try:
        system_status = SystemStatusDashboard.get_system_status()
        return render_template('monitoring/dashboard.html', status=system_status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@error_monitoring_bp.route('/monitoring/performance')
@admin_required
@rate_limit('admin', {'requests': 20, 'window': 3600})
def performance_monitoring():
    """Performance monitoring endpoint."""
    try:
        if hasattr(current_app, 'performance_monitor'):
            metrics = current_app.performance_monitor.get_performance_summary()
        else:
            metrics = {'error': 'Performance monitor not initialized'}
        
        return jsonify({
            'success': True,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@error_monitoring_bp.route('/monitoring/errors')
@admin_required
@rate_limit('admin', {'requests': 20, 'window': 3600})
def error_monitoring():
    """Error monitoring endpoint."""
    try:
        if hasattr(current_app, 'error_reporter'):
            error_summary = current_app.error_reporter.get_error_summary()
        else:
            error_summary = {'error': 'Error reporter not initialized'}
        
        return jsonify({
            'success': True,
            'errors': error_summary,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@error_monitoring_bp.route('/monitoring/system-status')
@admin_required
@rate_limit('admin', {'requests': 20, 'window': 3600})
def system_status():
    """System status endpoint."""
    try:
        status = SystemStatusDashboard.get_system_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@error_monitoring_bp.route('/monitoring/alerts')
@admin_required
@rate_limit('admin', {'requests': 10, 'window': 3600})
def get_alerts():
    """Get system alerts."""
    try:
        alerts = []
        
        if hasattr(current_app, 'redis_client'):
            # Get error alerts
            error_alerts = current_app.redis_client.lrange("error_alerts", 0, -1)
            for alert_json in error_alerts:
                try:
                    alert = json.loads(alert_json)
                    alerts.append(alert)
                except:
                    continue
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# API Endpoints for AJAX

@error_monitoring_bp.route('/api/monitoring/health')
@rate_limit('api', {'requests': 50, 'window': 3600})
def api_health_check():
    """API endpoint for health check."""
    return health_check()


@error_monitoring_bp.route('/api/monitoring/performance')
@admin_required
@rate_limit('api', {'requests': 20, 'window': 3600})
def api_performance_monitoring():
    """API endpoint for performance monitoring."""
    return performance_monitoring()


@error_monitoring_bp.route('/api/monitoring/errors')
@admin_required
@rate_limit('api', {'requests': 20, 'window': 3600})
def api_error_monitoring():
    """API endpoint for error monitoring."""
    return error_monitoring()


@error_monitoring_bp.route('/api/monitoring/system-status')
@admin_required
@rate_limit('api', {'requests': 20, 'window': 3600})
def api_system_status():
    """API endpoint for system status."""
    return system_status()


@error_monitoring_bp.route('/api/monitoring/alerts')
@admin_required
@rate_limit('api', {'requests': 10, 'window': 3600})
def api_get_alerts():
    """API endpoint for system alerts."""
    return get_alerts() 