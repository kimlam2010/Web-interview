"""
Mekong Recruitment System - Flask Application Factory

This module initializes the Flask application with proper configuration,
database setup, and extension registration following AGENT_RULES_DEVELOPER.
"""

import os
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_app(config_name='development'):
    """
    Application factory pattern for Flask app creation.
    
    Args:
        config_name (str): Configuration environment name
        
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name == 'production':
        from .config import ProductionConfig
        app.config.from_object(ProductionConfig)
    elif config_name == 'testing':
        from .config import TestingConfig
        app.config.from_object(TestingConfig)
    else:
        from .config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Vui lòng đăng nhập để truy cập trang này.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from .auth import auth_bp
    from .main import main_bp
    from .admin import admin_bp
    from .hr import hr_bp
    from .interview import interview_bp
    from .candidate import candidate_bp
    from .candidate_auth import candidate_auth_bp
    from .questions import questions_bp
    from .assessment import assessment_bp
    from .link_management import link_management_bp
    from .pdf_export import pdf_export_bp
    from .executive_decision import executive_decision_bp
    from .dashboard import dashboard_bp
    from .step2_questions import step2_questions_bp
    from .step3_questions import step3_questions_bp
    from .report_generation import report_generation_bp
    from .data_analytics import data_analytics_bp
    from .performance_optimization import performance_bp
    from .error_monitoring import error_monitoring_bp
    from .production_deployment import production_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(hr_bp, url_prefix='/hr')
    app.register_blueprint(interview_bp, url_prefix='/interview')
    app.register_blueprint(candidate_bp, url_prefix='/candidate')
    app.register_blueprint(candidate_auth_bp, url_prefix='/candidate')
    app.register_blueprint(questions_bp, url_prefix='/questions')
    app.register_blueprint(assessment_bp, url_prefix='/assessment')
    app.register_blueprint(link_management_bp, url_prefix='/links')
    app.register_blueprint(pdf_export_bp, url_prefix='/pdf')
    app.register_blueprint(executive_decision_bp, url_prefix='/executive')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(step2_questions_bp, url_prefix='/step2')
    app.register_blueprint(step3_questions_bp, url_prefix='/step3')
    app.register_blueprint(report_generation_bp, url_prefix='/reports')
    app.register_blueprint(data_analytics_bp, url_prefix='/analytics')
    app.register_blueprint(performance_bp, url_prefix='/performance')
    app.register_blueprint(error_monitoring_bp, url_prefix='/monitoring')
    app.register_blueprint(production_bp, url_prefix='/production')
    
    # Initialize security components
    try:
        import redis
        redis_client = redis.Redis(
            host=app.config.get('REDIS_HOST', 'localhost'),
            port=app.config.get('REDIS_PORT', 6379),
            db=app.config.get('REDIS_DB', 0),
            decode_responses=True
        )
        from .security import init_security
        init_security(redis_client)
        app.logger.info("Security components initialized successfully")
    except ImportError:
        app.logger.warning("Redis not available, security features limited")
    except Exception as e:
        app.logger.error(f"Failed to initialize security: {e}")
    
    # Load instance config overrides from instance/system_config.json
    try:
        instance_cfg_path = os.path.join(app.instance_path, 'system_config.json')
        if os.path.exists(instance_cfg_path):
            import json
            with open(instance_cfg_path, 'r', encoding='utf-8') as f:
                overrides = json.load(f)
            # Update Flask config
            app.config.update(overrides or {})
            # Apply CORS headers if configured (simple)
            cors = (overrides.get('SECURITY_POLICY') or {}).get('cors_allowed_origins')
            if cors:
                @app.after_request
                def _apply_cors(resp):
                    resp.headers['Access-Control-Allow-Origin'] = ','.join(cors)
                    resp.headers['Vary'] = 'Origin'
                    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                    return resp
            # Apply session lifetime if provided
            session_hours = overrides.get('SESSION_TIMEOUT_HOURS')
            if session_hours:
                app.permanent_session_lifetime = timedelta(hours=int(session_hours))
            app.logger.info('Loaded system_config.json from instance directory')
    except Exception as e:
        app.logger.error(f"Failed to load instance/system_config.json: {e}")

    # Register CLI commands
    from .commands import init_db, create_admin, load_sample_data, reset_db
    app.cli.add_command(init_db)
    app.cli.add_command(create_admin)
    app.cli.add_command(load_sample_data)
    app.cli.add_command(reset_db)
    
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Enable debug mode for better error messages
    app.config['DEBUG'] = True
    app.config['TESTING'] = False
    
    # Add error handlers
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    # Register context processors
    register_context_processors(app)
    
    return app

def register_context_processors(app):
    """Register context processors for template variables."""
    
    @app.context_processor
    def inject_config():
        """Inject configuration variables into templates."""
        return {
            'COMPANY_NAME': app.config.get('COMPANY_NAME', 'Mekong Technology'),
            'COMPANY_LOGO': app.config.get('COMPANY_LOGO', 'static/img/mekong_logo.png')
        }
    @app.context_processor
    def inject_user_roles():
        """Inject user roles configuration into templates."""
        return {
            'USER_ROLES': app.config.get('USER_ROLES', {})
        }

# Import at the end to avoid circular imports
from flask import render_template 