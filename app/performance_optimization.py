"""
Performance Optimization Module

Comprehensive performance optimization system with database query optimization,
Redis caching, pagination, lazy loading, background tasks, and CDN integration.
"""

import redis
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import text, and_, or_, func, desc
from sqlalchemy.orm import joinedload, selectinload
from app.models import db, Candidate, Position, AssessmentResult, InterviewEvaluation
from app.decorators import admin_required
from app.security import audit_log, rate_limit

performance_bp = Blueprint('performance', __name__)


class DatabaseQueryOptimizer:
    """Database query optimization utilities."""
    
    @staticmethod
    def optimize_candidate_queries():
        """Optimize candidate-related queries with proper joins and indexing."""
        # Example optimized query with eager loading
        candidates = db.session.query(Candidate)\
            .options(
                joinedload(Candidate.position),
                joinedload(Candidate.assessment_results),
                joinedload(Candidate.interview_evaluations)
            )\
            .filter(Candidate.status == 'active')\
            .all()
        
        return candidates
    
    @staticmethod
    def optimize_assessment_queries():
        """Optimize assessment result queries."""
        results = db.session.query(AssessmentResult)\
            .options(
                joinedload(AssessmentResult.candidate),
                joinedload(AssessmentResult.question)
            )\
            .filter(AssessmentResult.completed_at >= datetime.now() - timedelta(days=30))\
            .all()
        
        return results
    
    @staticmethod
    def create_database_indexes():
        """Create database indexes for frequently queried fields."""
        indexes = [
            # Candidate indexes
            "CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status)",
            "CREATE INDEX IF NOT EXISTS idx_candidates_position_id ON candidates(position_id)",
            "CREATE INDEX IF NOT EXISTS idx_candidates_created_at ON candidates(created_at)",
            
            # Assessment result indexes
            "CREATE INDEX IF NOT EXISTS idx_assessment_results_candidate_id ON assessment_results(candidate_id)",
            "CREATE INDEX IF NOT EXISTS idx_assessment_results_completed_at ON assessment_results(completed_at)",
            "CREATE INDEX IF NOT EXISTS idx_assessment_results_status ON assessment_results(status)",
            
            # Interview evaluation indexes
            "CREATE INDEX IF NOT EXISTS idx_interview_evaluations_candidate_id ON interview_evaluations(candidate_id)",
            "CREATE INDEX IF NOT EXISTS idx_interview_evaluations_interviewer_id ON interview_evaluations(interviewer_id)",
            "CREATE INDEX IF NOT EXISTS idx_interview_evaluations_evaluated_at ON interview_evaluations(evaluated_at)",
            
            # User indexes
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            
            # Question indexes
            "CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category)",
            "CREATE INDEX IF NOT EXISTS idx_questions_is_active ON questions(is_active)",
            
            # Position indexes
            "CREATE INDEX IF NOT EXISTS idx_positions_department ON positions(department)",
            "CREATE INDEX IF NOT EXISTS idx_positions_level ON positions(level)"
        ]
        
        for index_sql in indexes:
            try:
                db.session.execute(text(index_sql))
                db.session.commit()
            except Exception as e:
                current_app.logger.warning(f"Failed to create index: {e}")
    
    @staticmethod
    def analyze_slow_queries():
        """Analyze and identify slow queries."""
        # This would integrate with database monitoring tools
        # For now, we'll create a basic query analysis
        slow_queries = []
        
        # Example slow query detection
        start_time = time.time()
        candidates = db.session.query(Candidate).all()
        execution_time = time.time() - start_time
        
        if execution_time > 1.0:  # More than 1 second
            slow_queries.append({
                'query': 'SELECT * FROM candidates',
                'execution_time': execution_time,
                'suggestion': 'Add proper indexing and limit results'
            })
        
        return slow_queries


class RedisCacheManager:
    """Redis caching system for performance optimization."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hour default
    
    def cache_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments."""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ":".join(key_parts)
    
    def get_cached_data(self, key: str) -> Optional[Dict]:
        """Get data from cache."""
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            current_app.logger.error(f"Cache get error: {e}")
        return None
    
    def set_cached_data(self, key: str, data: Dict, ttl: int = None) -> bool:
        """Set data in cache."""
        try:
            ttl = ttl or self.default_ttl
            self.redis.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            current_app.logger.error(f"Cache set error: {e}")
            return False
    
    def invalidate_cache(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
        except Exception as e:
            current_app.logger.error(f"Cache invalidation error: {e}")
        return 0
    
    def cache_candidate_data(self, candidate_id: int, data: Dict) -> bool:
        """Cache candidate-specific data."""
        key = self.cache_key("candidate", candidate_id)
        return self.set_cached_data(key, data, ttl=1800)  # 30 minutes
    
    def get_cached_candidate_data(self, candidate_id: int) -> Optional[Dict]:
        """Get cached candidate data."""
        key = self.cache_key("candidate", candidate_id)
        return self.get_cached_data(key)
    
    def cache_assessment_results(self, position_id: int, data: Dict) -> bool:
        """Cache assessment results by position."""
        key = self.cache_key("assessment_results", position_id)
        return self.set_cached_data(key, data, ttl=900)  # 15 minutes
    
    def get_cached_assessment_results(self, position_id: int) -> Optional[Dict]:
        """Get cached assessment results."""
        key = self.cache_key("assessment_results", position_id)
        return self.get_cached_data(key)
    
    def cache_dashboard_metrics(self, user_id: int, data: Dict) -> bool:
        """Cache dashboard metrics for user."""
        key = self.cache_key("dashboard_metrics", user_id)
        return self.set_cached_data(key, data, ttl=600)  # 10 minutes
    
    def get_cached_dashboard_metrics(self, user_id: int) -> Optional[Dict]:
        """Get cached dashboard metrics."""
        key = self.cache_key("dashboard_metrics", user_id)
        return self.get_cached_data(key)


class PaginationManager:
    """Pagination system for large datasets."""
    
    @staticmethod
    def paginate_query(query, page: int = 1, per_page: int = 20):
        """Apply pagination to SQLAlchemy query."""
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            'items': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_prev': page > 1,
                'has_next': page * per_page < total
            }
        }
    
    @staticmethod
    def paginate_candidates(page: int = 1, per_page: int = 20, filters: Dict = None):
        """Paginate candidates with optional filters."""
        query = db.session.query(Candidate)
        
        if filters:
            if filters.get('status'):
                query = query.filter(Candidate.status == filters['status'])
            if filters.get('position_id'):
                query = query.filter(Candidate.position_id == filters['position_id'])
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Candidate.name.ilike(search_term),
                        Candidate.email.ilike(search_term)
                    )
                )
        
        return PaginationManager.paginate_query(query, page, per_page)
    
    @staticmethod
    def paginate_assessment_results(page: int = 1, per_page: int = 20, filters: Dict = None):
        """Paginate assessment results."""
        query = db.session.query(AssessmentResult)
        
        if filters:
            if filters.get('status'):
                query = query.filter(AssessmentResult.status == filters['status'])
            if filters.get('date_from'):
                query = query.filter(AssessmentResult.completed_at >= filters['date_from'])
            if filters.get('date_to'):
                query = query.filter(AssessmentResult.completed_at <= filters['date_to'])
        
        return PaginationManager.paginate_query(query, page, per_page)


class LazyLoadingManager:
    """Lazy loading system for UI components."""
    
    @staticmethod
    def lazy_load_candidates(page: int = 1, per_page: int = 10):
        """Lazy load candidates for infinite scroll."""
        return PaginationManager.paginate_candidates(page, per_page)
    
    @staticmethod
    def lazy_load_assessment_results(page: int = 1, per_page: int = 10):
        """Lazy load assessment results."""
        return PaginationManager.paginate_assessment_results(page, per_page)
    
    @staticmethod
    def lazy_load_interview_evaluations(page: int = 1, per_page: int = 10):
        """Lazy load interview evaluations."""
        query = db.session.query(InterviewEvaluation)
        return PaginationManager.paginate_query(query, page, per_page)


class BackgroundTaskProcessor:
    """Background task processing system."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.task_queue = "background_tasks"
    
    def enqueue_task(self, task_type: str, data: Dict) -> str:
        """Enqueue a background task."""
        task_id = f"{task_type}_{int(time.time())}"
        task_data = {
            'id': task_id,
            'type': task_type,
            'data': data,
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        try:
            self.redis.lpush(self.task_queue, json.dumps(task_data))
            return task_id
        except Exception as e:
            current_app.logger.error(f"Failed to enqueue task: {e}")
            return None
    
    def process_background_tasks(self):
        """Process background tasks from queue."""
        while True:
            try:
                # Get task from queue
                task_data = self.redis.brpop(self.task_queue, timeout=1)
                if not task_data:
                    continue
                
                task = json.loads(task_data[1])
                self.execute_task(task)
                
            except Exception as e:
                current_app.logger.error(f"Background task processing error: {e}")
                time.sleep(5)
    
    def execute_task(self, task: Dict):
        """Execute a specific background task."""
        task_type = task['type']
        task_id = task['id']
        
        try:
            if task_type == 'generate_report':
                self.generate_report_task(task['data'])
            elif task_type == 'send_notification':
                self.send_notification_task(task['data'])
            elif task_type == 'update_statistics':
                self.update_statistics_task(task['data'])
            elif task_type == 'cleanup_expired_data':
                self.cleanup_expired_data_task(task['data'])
            else:
                current_app.logger.warning(f"Unknown task type: {task_type}")
            
            # Update task status
            task['status'] = 'completed'
            task['completed_at'] = datetime.now().isoformat()
            
        except Exception as e:
            current_app.logger.error(f"Task execution failed: {e}")
            task['status'] = 'failed'
            task['error'] = str(e)
    
    def generate_report_task(self, data: Dict):
        """Background task for report generation."""
        # This would integrate with the report generation system
        current_app.logger.info(f"Generating report: {data}")
    
    def send_notification_task(self, data: Dict):
        """Background task for sending notifications."""
        # This would integrate with the email system
        current_app.logger.info(f"Sending notification: {data}")
    
    def update_statistics_task(self, data: Dict):
        """Background task for updating statistics."""
        # This would update cached statistics
        current_app.logger.info(f"Updating statistics: {data}")
    
    def cleanup_expired_data_task(self, data: Dict):
        """Background task for cleaning up expired data."""
        # This would clean up old data
        current_app.logger.info(f"Cleaning up expired data: {data}")


class CDNIntegrationManager:
    """CDN integration for static assets."""
    
    @staticmethod
    def get_cdn_url(asset_path: str) -> str:
        """Get CDN URL for static asset."""
        cdn_base_url = current_app.config.get('CDN_BASE_URL', '')
        
        if cdn_base_url:
            return f"{cdn_base_url.rstrip('/')}/{asset_path.lstrip('/')}"
        else:
            return f"/static/{asset_path}"
    
    @staticmethod
    def optimize_static_assets():
        """Optimize static assets for CDN delivery."""
        optimizations = {
            'css_files': [
                'css/main.css',
                'css/bootstrap.min.css',
                'css/fontawesome.min.css'
            ],
            'js_files': [
                'js/main.js',
                'js/bootstrap.bundle.min.js',
                'js/chart.js'
            ],
            'image_files': [
                'img/mekong_logo.png',
                'img/favicon.ico'
            ]
        }
        
        return optimizations
    
    @staticmethod
    def generate_asset_manifest():
        """Generate asset manifest for versioning."""
        manifest = {
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat(),
            'assets': {
                'css': {
                    'main.css': 'css/main.css?v=1.0.0',
                    'bootstrap.min.css': 'css/bootstrap.min.css?v=5.3.0'
                },
                'js': {
                    'main.js': 'js/main.js?v=1.0.0',
                    'bootstrap.bundle.min.js': 'js/bootstrap.bundle.min.js?v=5.3.0'
                },
                'images': {
                    'logo': 'img/mekong_logo.png?v=1.0.0'
                }
            }
        }
        
        return manifest


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.metrics_prefix = "performance_metrics"
    
    def record_query_time(self, query_name: str, execution_time: float):
        """Record database query execution time."""
        key = f"{self.metrics_prefix}:query_times"
        try:
            self.redis.hset(key, query_name, execution_time)
            self.redis.expire(key, 86400)  # 24 hours
        except Exception as e:
            current_app.logger.error(f"Failed to record query time: {e}")
    
    def record_api_response_time(self, endpoint: str, response_time: float):
        """Record API endpoint response time."""
        key = f"{self.metrics_prefix}:api_times"
        try:
            self.redis.hset(key, endpoint, response_time)
            self.redis.expire(key, 86400)  # 24 hours
        except Exception as e:
            current_app.logger.error(f"Failed to record API time: {e}")
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics."""
        metrics = {}
        
        try:
            # Get query times
            query_times = self.redis.hgetall(f"{self.metrics_prefix}:query_times")
            metrics['query_times'] = {k: float(v) for k, v in query_times.items()}
            
            # Get API response times
            api_times = self.redis.hgetall(f"{self.metrics_prefix}:api_times")
            metrics['api_times'] = {k: float(v) for k, v in api_times.items()}
            
            # Calculate averages
            if metrics['query_times']:
                metrics['avg_query_time'] = sum(metrics['query_times'].values()) / len(metrics['query_times'])
            else:
                metrics['avg_query_time'] = 0
            
            if metrics['api_times']:
                metrics['avg_api_time'] = sum(metrics['api_times'].values()) / len(metrics['api_times'])
            else:
                metrics['avg_api_time'] = 0
            
        except Exception as e:
            current_app.logger.error(f"Failed to get performance metrics: {e}")
            metrics = {'error': str(e)}
        
        return metrics


# Performance monitoring decorator
def monitor_performance(operation_type: str):
    """Decorator to monitor performance of functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Record performance metric
                if hasattr(current_app, 'performance_monitor'):
                    if operation_type == 'query':
                        current_app.performance_monitor.record_query_time(
                            func.__name__, execution_time
                        )
                    elif operation_type == 'api':
                        current_app.performance_monitor.record_api_response_time(
                            func.__name__, execution_time
                        )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                current_app.logger.error(f"Performance monitoring error: {e}")
                raise
        
        return wrapper
    return decorator


# Route Definitions

@performance_bp.route('/performance/optimize-database')
@admin_required
@rate_limit('admin', {'requests': 10, 'window': 3600})
@audit_log('optimize_database')
def optimize_database():
    """Optimize database performance."""
    try:
        # Create database indexes
        DatabaseQueryOptimizer.create_database_indexes()
        
        # Analyze slow queries
        slow_queries = DatabaseQueryOptimizer.analyze_slow_queries()
        
        return jsonify({
            'success': True,
            'message': 'Database optimization completed',
            'slow_queries': slow_queries
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@performance_bp.route('/performance/cache-status')
@admin_required
@rate_limit('admin', {'requests': 20, 'window': 3600})
def get_cache_status():
    """Get Redis cache status."""
    try:
        redis_client = current_app.redis_client
        info = redis_client.info()
        
        return jsonify({
            'success': True,
            'cache_info': {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory_human', '0B'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@performance_bp.route('/performance/metrics')
@admin_required
@rate_limit('admin', {'requests': 20, 'window': 3600})
def get_performance_metrics():
    """Get performance metrics."""
    try:
        if hasattr(current_app, 'performance_monitor'):
            metrics = current_app.performance_monitor.get_performance_metrics()
        else:
            metrics = {'error': 'Performance monitor not initialized'}
        
        return jsonify({
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@performance_bp.route('/performance/lazy-load/<data_type>')
@rate_limit('api', {'requests': 100, 'window': 3600})
def lazy_load_data(data_type: str):
    """Lazy load data for UI components."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        if data_type == 'candidates':
            result = LazyLoadingManager.lazy_load_candidates(page, per_page)
        elif data_type == 'assessment_results':
            result = LazyLoadingManager.lazy_load_assessment_results(page, per_page)
        elif data_type == 'interview_evaluations':
            result = LazyLoadingManager.lazy_load_interview_evaluations(page, per_page)
        else:
            return jsonify({'success': False, 'error': 'Invalid data type'}), 400
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@performance_bp.route('/performance/background-task', methods=['POST'])
@admin_required
@rate_limit('admin', {'requests': 10, 'window': 3600})
@audit_log('enqueue_background_task')
def enqueue_background_task():
    """Enqueue a background task."""
    try:
        data = request.get_json()
        task_type = data.get('task_type')
        task_data = data.get('task_data', {})
        
        if not task_type:
            return jsonify({'success': False, 'error': 'Task type required'}), 400
        
        if hasattr(current_app, 'background_processor'):
            task_id = current_app.background_processor.enqueue_task(task_type, task_data)
            
            if task_id:
                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'message': 'Task enqueued successfully'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to enqueue task'}), 500
        else:
            return jsonify({'success': False, 'error': 'Background processor not initialized'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@performance_bp.route('/performance/cdn-assets')
@rate_limit('api', {'requests': 50, 'window': 3600})
def get_cdn_assets():
    """Get CDN-optimized asset URLs."""
    try:
        optimizations = CDNIntegrationManager.optimize_static_assets()
        manifest = CDNIntegrationManager.generate_asset_manifest()
        
        return jsonify({
            'success': True,
            'optimizations': optimizations,
            'manifest': manifest
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# API Endpoints for AJAX

@performance_bp.route('/api/performance/optimize-database')
@admin_required
@rate_limit('api', {'requests': 5, 'window': 3600})
def api_optimize_database():
    """API endpoint for database optimization."""
    return optimize_database()


@performance_bp.route('/api/performance/cache-status')
@admin_required
@rate_limit('api', {'requests': 20, 'window': 3600})
def api_cache_status():
    """API endpoint for cache status."""
    return get_cache_status()


@performance_bp.route('/api/performance/metrics')
@admin_required
@rate_limit('api', {'requests': 20, 'window': 3600})
def api_performance_metrics():
    """API endpoint for performance metrics."""
    return get_performance_metrics()


@performance_bp.route('/api/performance/lazy-load/<data_type>')
@rate_limit('api', {'requests': 100, 'window': 3600})
def api_lazy_load_data(data_type: str):
    """API endpoint for lazy loading data."""
    return lazy_load_data(data_type) 