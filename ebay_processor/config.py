# ebay_processor/config.py
"""
Configuración de la Aplicación.

Carga las configuraciones desde variables de entorno.
Es una clase simple que sirve como un único lugar de verdad para
todas las variables de configuración.
"""

import os
from datetime import timedelta

class Config:
    """
    Clase de configuración base. Carga valores desde el entorno.
    """
    # Clave secreta para la seguridad de la sesión de Flask.
    # Es CRÍTICO que esta sea una cadena larga, aleatoria y secreta.
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Credenciales de administrador para el login.
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')

    # Configuración de la sesión de Flask.
    # Usamos el sistema de archivos para que sea persistente.
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24) # Las sesiones duran 24 horas.
    SESSION_USE_SIGNER = False # Temporarily disable signing to avoid bytes/string issues
    SESSION_KEY_PREFIX = 'ebay_session:'
    SESSION_FILE_DIR = os.environ.get('FLASK_SESSION_DIR', 'data/sessions')
    SESSION_FILE_THRESHOLD = 500
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    # Rutas a directorios persistentes.
    # Se recomienda que en producción, estas rutas apunten a un volumen montado.
    # En create_app, se asegura que estos directorios existan.
    LOG_DIR = os.path.abspath(os.environ.get('LOG_DIR', 'data/logs'))
    OUTPUT_DIR = os.path.abspath(os.environ.get('OUTPUT_DIR', 'data/output'))
    FLASK_SESSION_DIR = os.path.abspath(os.environ.get('FLASK_SESSION_DIR', 'data/sessions'))
    PROCESS_STORE_DIR = os.path.abspath(os.environ.get('PROCESS_STORE_DIR', 'data/processes'))
    
    # Rutas a archivos de datos de referencia.
    MATLIST_CSV_PATH = os.environ.get('MATLIST_CSV_PATH', 'data/ktypemaster3.csv')
    # Este archivo JSON se usará para guardar el estado de los tokens de eBay.
    EBAY_CONFIG_JSON_PATH = os.environ.get('EBAY_CONFIG_JSON_PATH', 'data/ebay_tokens.json')

    # Credenciales de la API de eBay.
    EBAY_APP_ID = os.environ.get('EBAY_APP_ID')
    EBAY_CERT_ID = os.environ.get('EBAY_CERT_ID')
    EBAY_DEV_ID = os.environ.get('EBAY_DEV_ID')

    # Configuración de las tiendas.
    # Iniciales usadas para nombrar archivos.
    STORE_INITIALS = {
        'carmatsking_uk': 'MK',
        'car_mats_custom': 'CC',
        'vwcarmatsuk': 'VW',
        'custom-fit-car-mats': 'CF',
        'car-mats-to-fit': 'CM',
        # Añade más tiendas aquí si es necesario
    }

    # Cuentas de tienda con sus refresh tokens.
    # El formato es una lista de diccionarios. Se carga dinámicamente.
    # El bucle buscará EBAY_STORE_1_ID, EBAY_STORE_1_REFRESH_TOKEN, etc.
    # en el archivo .env hasta que no encuentre más.
    EBAY_STORE_ACCOUNTS = []
    i = 1
    while True:
        account_id = os.environ.get(f'EBAY_STORE_{i}_ID')
        refresh_token = os.environ.get(f'EBAY_STORE_{i}_REFRESH_TOKEN')
        if account_id and refresh_token:
            EBAY_STORE_ACCOUNTS.append({
                'account_id': account_id,
                'refresh_token': refresh_token
            })
            i += 1
        else:
            break

    # Configuración del planificador de tareas.
    ENABLE_SCHEDULER = os.environ.get('ENABLE_SCHEDULER', 'True').lower() == 'true'
    SESSION_LIFETIME_HOURS = 24
    SESSION_CLEANUP_INTERVAL_HOURS = 6
    PROCESS_FILE_RETENTION_HOURS = 48
    PROCESS_CLEANUP_INTERVAL_HOURS = 12
    
    # Parámetros de procesamiento
    DEFAULT_ORDER_FETCH_DAYS = 29