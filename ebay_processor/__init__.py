# ebay_processor/__init__.py
"""
Application Entry Point and Application Factory.

This file contains the `create_app` function, which is responsible for
building and configuring the Flask application instance.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_session import Session



# Import our configuration class
from .config import Config

# Import scheduled cleanup functions
from .persistence.process_store import ProcessStore
from .utils.file_utils import cleanup_directory


def create_app(config_class=Config):
    """
    Application Factory: Creates and configures the Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=True)

    # 1. Load configuration
    # ---------------------
    app.config.from_object(config_class)
    
    # Ensure necessary directories exist
    for path_key in ['LOG_DIR', 'OUTPUT_DIR', 'FLASK_SESSION_DIR', 'PROCESS_STORE_DIR']:
        path = app.config.get(path_key)
        if path:
            os.makedirs(path, exist_ok=True)
        else:
            # If an essential path is not configured, it's a fatal error.
            raise ValueError(f"Configuration path '{path_key}' is not defined.")
    
    # Set the session file directory to the correct path
    app.config['SESSION_FILE_DIR'] = app.config['FLASK_SESSION_DIR']

    # 2. Configure Logging
    # --------------------
    # Configure a rotating log to prevent files from growing indefinitely.
    log_file = os.path.join(app.config['LOG_DIR'], 'app.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('eBay Order Processor application starting...')

    # 3. Configure Session Management (BACK TO SIMPLE APPROACH)
    # ----------------------------------------------------------
    Session(app)

    # 3.5. Add context processor to make 'now' available in all templates
    # ------------------------------------------------------------------
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}


    # 4. Register Blueprints
    # ----------------------
    # This is where we connect all our routes to the application.
    from .web.routes.auth import auth_bp
    from .web.routes.processing import processing_bp
    from .web.routes.files import files_bp
    from .web.routes.tracking import tracking_bp
    from .web.routes.health import health_bp  # Assuming we'll create one for /health

    app.register_blueprint(auth_bp)
    app.register_blueprint(processing_bp, url_prefix='/')
    app.register_blueprint(files_bp, url_prefix='/files')
    app.register_blueprint(tracking_bp, url_prefix='/tracking')
    app.register_blueprint(health_bp, url_prefix='/')

    app.logger.info("Blueprints registered successfully.")

    # 5. Configure and Start Task Scheduler
    # --------------------------------------
    # We use APScheduler to run periodic cleanup tasks in the background.
    if app.config.get('ENABLE_SCHEDULER', True):
        scheduler = BackgroundScheduler(daemon=True)
        
        # Task 1: Clean up old session files.
        scheduler.add_job(
            func=cleanup_directory,
            trigger='interval',
            hours=app.config.get('SESSION_CLEANUP_INTERVAL_HOURS', 6),
            args=[
                app.config['FLASK_SESSION_DIR'],
                'session_*',
                app.config.get('SESSION_LIFETIME_HOURS', 24)
            ],
            id='cleanup_sessions_job',
            replace_existing=True
        )

        # Task 2: Clean up old process state files.
        def cleanup_process_store_job():
            with app.app_context(): # Necessary for the job to access config
                store = ProcessStore(app.config['PROCESS_STORE_DIR'])
                store.scheduled_cleanup(app.config.get('PROCESS_FILE_RETENTION_HOURS', 48))

        scheduler.add_job(
            func=cleanup_process_store_job,
            trigger='interval',
            hours=app.config.get('PROCESS_CLEANUP_INTERVAL_HOURS', 12),
            id='cleanup_process_store_job',
            replace_existing=True
        )
        
        scheduler.start()
        app.logger.info("Scheduler started with scheduled cleanup tasks.")

        # It's good practice to shut down the scheduler cleanly when the app closes.
        import atexit
        atexit.register(lambda: scheduler.shutdown())

    return app