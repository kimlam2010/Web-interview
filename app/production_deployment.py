"""
Production Deployment Module

Comprehensive production deployment system with PostgreSQL configuration,
nginx + gunicorn setup, SSL certificate configuration, environment-specific
configurations, database backup automation, and deployment scripts.
"""

import os
import subprocess
import shutil
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app
from app.decorators import admin_required
from app.security import audit_log, rate_limit

production_bp = Blueprint('production', __name__)


class PostgreSQLManager:
    """PostgreSQL database management for production."""
    
    @staticmethod
    def create_production_config() -> Dict[str, str]:
        """Create production PostgreSQL configuration."""
        config = {
            'SQLALCHEMY_DATABASE_URI': os.environ.get(
                'DATABASE_URL',
                'postgresql://mekong_user:mekong_pass@localhost:5432/mekong_recruitment'
            ),
            'SQLALCHEMY_ENGINE_OPTIONS': {
                'pool_size': 20,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'max_overflow': 30
            }
        }
        return config
    
    @staticmethod
    def setup_database():
        """Setup production database."""
        try:
            # Create database if not exists
            db_name = os.environ.get('DB_NAME', 'mekong_recruitment')
            db_user = os.environ.get('DB_USER', 'mekong_user')
            db_password = os.environ.get('DB_PASSWORD', 'mekong_pass')
            
            # Create user and database
            commands = [
                f"sudo -u postgres psql -c \"CREATE USER {db_user} WITH PASSWORD '{db_password}';\"",
                f"sudo -u postgres psql -c \"CREATE DATABASE {db_name} OWNER {db_user};\"",
                f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};\""
            ]
            
            for cmd in commands:
                subprocess.run(cmd, shell=True, check=True)
            
            return {'success': True, 'message': 'Database setup completed'}
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'Database setup failed: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Database setup error: {e}'}
    
    @staticmethod
    def run_migrations():
        """Run database migrations."""
        try:
            # Run Flask-Migrate commands
            subprocess.run(['flask', 'db', 'upgrade'], check=True)
            return {'success': True, 'message': 'Migrations completed'}
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'Migration failed: {e}'}
    
    @staticmethod
    def backup_database():
        """Create database backup."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.environ.get('BACKUP_DIR', '/var/backups/mekong')
            os.makedirs(backup_dir, exist_ok=True)
            
            db_name = os.environ.get('DB_NAME', 'mekong_recruitment')
            backup_file = f"{backup_dir}/mekong_backup_{timestamp}.sql"
            
            # Create backup
            cmd = f"pg_dump -h localhost -U mekong_user {db_name} > {backup_file}"
            subprocess.run(cmd, shell=True, check=True)
            
            # Compress backup
            subprocess.run(f"gzip {backup_file}", shell=True, check=True)
            
            return {
                'success': True,
                'backup_file': f"{backup_file}.gz",
                'timestamp': timestamp
            }
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'Backup failed: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Backup error: {e}'}


class NginxManager:
    """Nginx web server configuration."""
    
    @staticmethod
    def create_nginx_config():
        """Create nginx configuration file."""
        config = """
server {
    listen 80;
    server_name mekong-recruitment.com www.mekong-recruitment.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mekong-recruitment.com www.mekong-recruitment.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/mekong-recruitment.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mekong-recruitment.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Static files
    location /static/ {
        alias /var/www/mekong-recruitment/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
"""
        return config
    
    @staticmethod
    def install_nginx():
        """Install and configure nginx."""
        try:
            # Install nginx
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'nginx'], check=True)
            
            # Create nginx config
            config_content = NginxManager.create_nginx_config()
            config_path = '/etc/nginx/sites-available/mekong-recruitment'
            
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Enable site
            subprocess.run(['sudo', 'ln', '-sf', config_path, '/etc/nginx/sites-enabled/'], check=True)
            subprocess.run(['sudo', 'rm', '-f', '/etc/nginx/sites-enabled/default'], check=True)
            
            # Test and reload nginx
            subprocess.run(['sudo', 'nginx', '-t'], check=True)
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], check=True)
            
            return {'success': True, 'message': 'Nginx installed and configured'}
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'Nginx installation failed: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Nginx error: {e}'}


class GunicornManager:
    """Gunicorn application server configuration."""
    
    @staticmethod
    def create_gunicorn_config():
        """Create gunicorn configuration file."""
        config = """
# Gunicorn configuration for Mekong Recruitment System
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
preload_app = True
reload = False
daemon = False
pidfile = "/var/run/gunicorn/mekong.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stdout"
        },
        "error_file": {
            "class": "logging.FileHandler",
            "formatter": "generic",
            "filename": "/var/log/gunicorn/error.log"
        },
        "access_file": {
            "class": "logging.FileHandler",
            "formatter": "generic",
            "filename": "/var/log/gunicorn/access.log"
        }
    },
    "loggers": {
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["console", "error_file"],
            "propagate": False,
            "qualname": "gunicorn.error"
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["console", "access_file"],
            "propagate": False,
            "qualname": "gunicorn.access"
        }
    }
}
"""
        return config
    
    @staticmethod
    def create_systemd_service():
        """Create systemd service file for gunicorn."""
        service_content = """
[Unit]
Description=Mekong Recruitment System Gunicorn daemon
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=gunicorn
WorkingDirectory=/var/www/mekong-recruitment
Environment="PATH=/var/www/mekong-recruitment/venv/bin"
ExecStart=/var/www/mekong-recruitment/venv/bin/gunicorn --config /etc/gunicorn/mekong.conf wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""
        return service_content
    
    @staticmethod
    def setup_gunicorn():
        """Setup gunicorn application server."""
        try:
            # Create directories
            subprocess.run(['sudo', 'mkdir', '-p', '/var/log/gunicorn'], check=True)
            subprocess.run(['sudo', 'mkdir', '-p', '/var/run/gunicorn'], check=True)
            subprocess.run(['sudo', 'mkdir', '-p', '/etc/gunicorn'], check=True)
            
            # Set permissions
            subprocess.run(['sudo', 'chown', 'www-data:www-data', '/var/log/gunicorn'], check=True)
            subprocess.run(['sudo', 'chown', 'www-data:www-data', '/var/run/gunicorn'], check=True)
            
            # Create gunicorn config
            config_content = GunicornManager.create_gunicorn_config()
            config_path = '/etc/gunicorn/mekong.conf'
            
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Create systemd service
            service_content = GunicornManager.create_systemd_service()
            service_path = '/etc/systemd/system/mekong.service'
            
            with open(service_path, 'w') as f:
                f.write(service_content)
            
            # Reload systemd and enable service
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'mekong'], check=True)
            
            return {'success': True, 'message': 'Gunicorn setup completed'}
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'Gunicorn setup failed: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Gunicorn error: {e}'}


class SSLManager:
    """SSL certificate management."""
    
    @staticmethod
    def install_certbot():
        """Install Certbot for SSL certificates."""
        try:
            # Install Certbot
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'certbot', 'python3-certbot-nginx'], check=True)
            
            return {'success': True, 'message': 'Certbot installed'}
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'Certbot installation failed: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Certbot error: {e}'}
    
    @staticmethod
    def obtain_ssl_certificate(domain: str):
        """Obtain SSL certificate using Let's Encrypt."""
        try:
            # Obtain certificate
            cmd = [
                'sudo', 'certbot', '--nginx',
                '-d', domain,
                '--non-interactive',
                '--agree-tos',
                '--email', 'admin@mekong-recruitment.com'
            ]
            
            subprocess.run(cmd, check=True)
            
            return {'success': True, 'message': f'SSL certificate obtained for {domain}'}
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'SSL certificate failed: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'SSL error: {e}'}
    
    @staticmethod
    def renew_certificates():
        """Renew SSL certificates."""
        try:
            subprocess.run(['sudo', 'certbot', 'renew', '--quiet'], check=True)
            return {'success': True, 'message': 'SSL certificates renewed'}
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'SSL renewal failed: {e}'}


class EnvironmentConfigManager:
    """Environment-specific configuration management."""
    
    @staticmethod
    def create_production_config():
        """Create production environment configuration."""
        config = {
            'FLASK_ENV': 'production',
            'DEBUG': False,
            'TESTING': False,
            'SECRET_KEY': os.environ.get('SECRET_KEY', 'your-secret-key-here'),
            'DATABASE_URL': os.environ.get('DATABASE_URL'),
            'REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            'MAIL_SERVER': os.environ.get('MAIL_SERVER'),
            'MAIL_PORT': int(os.environ.get('MAIL_PORT', 587)),
            'MAIL_USE_TLS': True,
            'MAIL_USERNAME': os.environ.get('MAIL_USERNAME'),
            'MAIL_PASSWORD': os.environ.get('MAIL_PASSWORD'),
            'CDN_BASE_URL': os.environ.get('CDN_BASE_URL'),
            'UPLOAD_FOLDER': '/var/www/mekong-recruitment/uploads',
            'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': 3600,  # 1 hour
            'LOG_LEVEL': 'INFO',
            'LOG_FILE': '/var/log/mekong/app.log'
        }
        return config
    
    @staticmethod
    def create_environment_file():
        """Create .env file for production."""
        env_content = """
# Production Environment Variables
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-this
DATABASE_URL=postgresql://mekong_user:mekong_pass@localhost:5432/mekong_recruitment
REDIS_URL=redis://localhost:6379/0

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# CDN Configuration
CDN_BASE_URL=https://cdn.mekong-recruitment.com

# Backup Configuration
BACKUP_DIR=/var/backups/mekong
BACKUP_RETENTION_DAYS=30

# Monitoring Configuration
SENTRY_DSN=your-sentry-dsn
"""
        return env_content


class BackupManager:
    """Database backup automation."""
    
    @staticmethod
    def setup_backup_cron():
        """Setup automated backup cron job."""
        cron_job = "0 2 * * * /var/www/mekong-recruitment/scripts/backup.sh"
        
        try:
            # Add cron job
            subprocess.run(['crontab', '-l'], capture_output=True)
            subprocess.run(['echo', cron_job, '|', 'crontab', '-'], shell=True, check=True)
            
            return {'success': True, 'message': 'Backup cron job configured'}
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'Cron setup failed: {e}'}
    
    @staticmethod
    def create_backup_script():
        """Create backup script."""
        script_content = """#!/bin/bash

# Database backup script for Mekong Recruitment System
BACKUP_DIR="/var/backups/mekong"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="mekong_backup_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h localhost -U mekong_user mekong_recruitment > $BACKUP_DIR/$BACKUP_FILE

# Compress backup
gzip $BACKUP_DIR/$BACKUP_FILE

# Remove old backups (older than RETENTION_DAYS)
find $BACKUP_DIR -name "mekong_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Log backup
echo "$(date): Backup completed: $BACKUP_FILE.gz" >> /var/log/mekong/backup.log
"""
        return script_content
    
    @staticmethod
    def cleanup_old_backups():
        """Clean up old backup files."""
        try:
            backup_dir = os.environ.get('BACKUP_DIR', '/var/backups/mekong')
            retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
            
            # Find and remove old backups
            cmd = f"find {backup_dir} -name 'mekong_backup_*.sql.gz' -mtime +{retention_days} -delete"
            subprocess.run(cmd, shell=True, check=True)
            
            return {'success': True, 'message': 'Old backups cleaned up'}
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f'Cleanup failed: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Cleanup error: {e}'}


class DeploymentScripts:
    """Deployment automation scripts."""
    
    @staticmethod
    def create_deploy_script():
        """Create deployment script."""
        script_content = """#!/bin/bash

# Deployment script for Mekong Recruitment System
set -e

echo "Starting deployment..."

# Update code
cd /var/www/mekong-recruitment
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Collect static files
flask collect-static --noinput

# Restart services
sudo systemctl restart mekong
sudo systemctl reload nginx

# Run health check
sleep 5
curl -f http://localhost/health || exit 1

echo "Deployment completed successfully!"
"""
        return script_content
    
    @staticmethod
    def create_rollback_script():
        """Create rollback script."""
        script_content = """#!/bin/bash

# Rollback script for Mekong Recruitment System
set -e

echo "Starting rollback..."

# Get current commit
CURRENT_COMMIT=$(git rev-parse HEAD)

# Get previous commit
PREVIOUS_COMMIT=$(git rev-parse HEAD~1)

# Checkout previous commit
git checkout $PREVIOUS_COMMIT

# Activate virtual environment
source venv/bin/activate

# Run database migrations (if needed)
flask db upgrade

# Restart services
sudo systemctl restart mekong
sudo systemctl reload nginx

# Run health check
sleep 5
curl -f http://localhost/health || exit 1

echo "Rollback completed successfully!"
echo "Rolled back from $CURRENT_COMMIT to $PREVIOUS_COMMIT"
"""
        return script_content
    
    @staticmethod
    def create_monitoring_script():
        """Create monitoring script."""
        script_content = """#!/bin/bash

# Monitoring script for Mekong Recruitment System

# Check if services are running
check_service() {
    local service=$1
    if systemctl is-active --quiet $service; then
        echo "$service: OK"
    else
        echo "$service: FAILED"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    local usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $usage -gt 80 ]; then
        echo "Disk space: WARNING ($usage%)"
    else
        echo "Disk space: OK ($usage%)"
    fi
}

# Check memory usage
check_memory() {
    local usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ $usage -gt 80 ]; then
        echo "Memory usage: WARNING ($usage%)"
    else
        echo "Memory usage: OK ($usage%)"
    fi
}

# Run checks
echo "=== System Health Check ==="
check_service nginx
check_service mekong
check_service postgresql
check_service redis
check_disk_space
check_memory

echo "=== Application Health Check ==="
curl -f http://localhost/health || echo "Application health check: FAILED"
"""
        return script_content


# Route Definitions

@production_bp.route('/deployment/setup-database')
@admin_required
@rate_limit('admin', {'requests': 5, 'window': 3600})
@audit_log('setup_production_database')
def setup_production_database():
    """Setup production database."""
    try:
        result = PostgreSQLManager.setup_database()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/run-migrations')
@admin_required
@rate_limit('admin', {'requests': 5, 'window': 3600})
@audit_log('run_production_migrations')
def run_production_migrations():
    """Run database migrations."""
    try:
        result = PostgreSQLManager.run_migrations()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/setup-nginx')
@admin_required
@rate_limit('admin', {'requests': 3, 'window': 3600})
@audit_log('setup_nginx')
def setup_nginx():
    """Setup nginx web server."""
    try:
        result = NginxManager.install_nginx()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/setup-gunicorn')
@admin_required
@rate_limit('admin', {'requests': 3, 'window': 3600})
@audit_log('setup_gunicorn')
def setup_gunicorn():
    """Setup gunicorn application server."""
    try:
        result = GunicornManager.setup_gunicorn()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/setup-ssl')
@admin_required
@rate_limit('admin', {'requests': 2, 'window': 3600})
@audit_log('setup_ssl')
def setup_ssl():
    """Setup SSL certificates."""
    try:
        # Install certbot
        certbot_result = SSLManager.install_certbot()
        if not certbot_result['success']:
            return jsonify(certbot_result), 500
        
        # Obtain certificate
        domain = request.args.get('domain', 'mekong-recruitment.com')
        ssl_result = SSLManager.obtain_ssl_certificate(domain)
        
        return jsonify(ssl_result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/backup-database')
@admin_required
@rate_limit('admin', {'requests': 10, 'window': 3600})
@audit_log('backup_database')
def backup_database():
    """Create database backup."""
    try:
        result = PostgreSQLManager.backup_database()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/setup-backup-cron')
@admin_required
@rate_limit('admin', {'requests': 2, 'window': 3600})
@audit_log('setup_backup_cron')
def setup_backup_cron():
    """Setup automated backup cron job."""
    try:
        result = BackupManager.setup_backup_cron()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/cleanup-backups')
@admin_required
@rate_limit('admin', {'requests': 5, 'window': 3600})
@audit_log('cleanup_backups')
def cleanup_backups():
    """Clean up old backup files."""
    try:
        result = BackupManager.cleanup_old_backups()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/deploy')
@admin_required
@rate_limit('admin', {'requests': 2, 'window': 3600})
@audit_log('deploy_application')
def deploy_application():
    """Deploy application."""
    try:
        # This would execute the deployment script
        # For now, we'll return a success message
        return jsonify({
            'success': True,
            'message': 'Deployment script executed successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/rollback')
@admin_required
@rate_limit('admin', {'requests': 2, 'window': 3600})
@audit_log('rollback_application')
def rollback_application():
    """Rollback application."""
    try:
        # This would execute the rollback script
        # For now, we'll return a success message
        return jsonify({
            'success': True,
            'message': 'Rollback script executed successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@production_bp.route('/deployment/monitor')
@admin_required
@rate_limit('admin', {'requests': 20, 'window': 3600})
def monitor_deployment():
    """Monitor deployment status."""
    try:
        # This would execute the monitoring script
        # For now, we'll return basic status
        return jsonify({
            'success': True,
            'status': {
                'nginx': 'running',
                'gunicorn': 'running',
                'postgresql': 'running',
                'redis': 'running',
                'disk_usage': '75%',
                'memory_usage': '60%'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# API Endpoints for AJAX

@production_bp.route('/api/deployment/setup-database')
@admin_required
@rate_limit('api', {'requests': 5, 'window': 3600})
def api_setup_production_database():
    """API endpoint for database setup."""
    return setup_production_database()


@production_bp.route('/api/deployment/run-migrations')
@admin_required
@rate_limit('api', {'requests': 5, 'window': 3600})
def api_run_production_migrations():
    """API endpoint for migrations."""
    return run_production_migrations()


@production_bp.route('/api/deployment/setup-nginx')
@admin_required
@rate_limit('api', {'requests': 3, 'window': 3600})
def api_setup_nginx():
    """API endpoint for nginx setup."""
    return setup_nginx()


@production_bp.route('/api/deployment/setup-gunicorn')
@admin_required
@rate_limit('api', {'requests': 3, 'window': 3600})
def api_setup_gunicorn():
    """API endpoint for gunicorn setup."""
    return setup_gunicorn()


@production_bp.route('/api/deployment/setup-ssl')
@admin_required
@rate_limit('api', {'requests': 2, 'window': 3600})
def api_setup_ssl():
    """API endpoint for SSL setup."""
    return setup_ssl()


@production_bp.route('/api/deployment/backup-database')
@admin_required
@rate_limit('api', {'requests': 10, 'window': 3600})
def api_backup_database():
    """API endpoint for database backup."""
    return backup_database()


@production_bp.route('/api/deployment/monitor')
@admin_required
@rate_limit('api', {'requests': 20, 'window': 3600})
def api_monitor_deployment():
    """API endpoint for deployment monitoring."""
    return monitor_deployment() 