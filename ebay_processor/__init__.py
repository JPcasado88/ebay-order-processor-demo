# ebay_processor/__init__.py
"""
Punto de Entrada de la Aplicación y Application Factory.

Este archivo contiene la función `create_app`, que es la responsable de
construir y configurar la instancia de la aplicación Flask.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_session import Session



# Importamos nuestra clase de configuración
from .config import Config

# Importamos las funciones de limpieza programada
from .persistence.process_store import ProcessStore
from .utils.file_utils import cleanup_directory


def create_app(config_class=Config):
    """
    Application Factory: Crea y configura la instancia de la aplicación Flask.
    """
    app = Flask(__name__, instance_relative_config=True)

    # 1. Cargar la configuración
    # --------------------------
    app.config.from_object(config_class)
    
    # Asegurarse de que los directorios necesarios existan
    for path_key in ['LOG_DIR', 'OUTPUT_DIR', 'FLASK_SESSION_DIR', 'PROCESS_STORE_DIR']:
        path = app.config.get(path_key)
        if path:
            os.makedirs(path, exist_ok=True)
        else:
            # Si una ruta esencial no está configurada, es un error fatal.
            raise ValueError(f"La ruta de configuración '{path_key}' no está definida.")
    
    # Set the session file directory to the correct path
    app.config['SESSION_FILE_DIR'] = app.config['FLASK_SESSION_DIR']

    # 2. Configurar el Logging
    # ------------------------
    # Se configura un log que rota para evitar que los archivos crezcan indefinidamente.
    log_file = os.path.join(app.config['LOG_DIR'], 'app.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Aplicación eBay Order Processor iniciándose...')

    # 3. Configurar la Gestión de Sesiones (VOLVEMOS A LA FORMA SIMPLE)
    # ------------------------------------
    Session(app)

    # 3.5. Add context processor to make 'now' available in all templates
    # ------------------------------------------------------------------
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}


    # 4. Registrar los Blueprints
    # ---------------------------
    # Aquí es donde conectamos todas nuestras rutas a la aplicación.
    from .web.routes.auth import auth_bp
    from .web.routes.processing import processing_bp
    from .web.routes.files import files_bp
    from .web.routes.tracking import tracking_bp
    from .web.routes.health import health_bp  # Asumiendo que crearemos uno para /health

    app.register_blueprint(auth_bp)
    app.register_blueprint(processing_bp, url_prefix='/')
    app.register_blueprint(files_bp, url_prefix='/files')
    app.register_blueprint(tracking_bp, url_prefix='/tracking')
    app.register_blueprint(health_bp, url_prefix='/')

    app.logger.info("Blueprints registrados exitosamente.")

    # 5. Configurar y Iniciar el Planificador de Tareas (Scheduler)
    # -----------------------------------------------------------
    # Usamos APScheduler para ejecutar tareas de limpieza periódicas en segundo plano.
    if app.config.get('ENABLE_SCHEDULER', True):
        scheduler = BackgroundScheduler(daemon=True)
        
        # Tarea 1: Limpiar archivos de sesión antiguos.
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

        # Tarea 2: Limpiar archivos de estado de procesos antiguos.
        def cleanup_process_store_job():
            with app.app_context(): # Necesario para que el job acceda a la config
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
        app.logger.info("Scheduler iniciado con tareas de limpieza programadas.")

        # Es una buena práctica apagar el scheduler de forma limpia cuando la app se cierra.
        import atexit
        atexit.register(lambda: scheduler.shutdown())

    return app