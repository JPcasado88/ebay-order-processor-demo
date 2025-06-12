# ebay_processor/config.py
"""
Application Configuration.

Loads configurations from environment variables.
A simple class that serves as a single source of truth for
all configuration variables.
"""

import os
from datetime import timedelta

class Config:
    """
    Base configuration class. Loads values from environment.
    """
    # Secret key for Flask session security.
    # It's CRITICAL that this is a long, random, and secret string.
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Administrator credentials for login.
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')

    # --- DEMO MODE CONFIGURATION ---
    # Set DEMO_MODE=true in environment to enable demo functionality
    # This allows the app to work without real eBay API integration
    DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'
    
    # Demo data paths (used when DEMO_MODE=true)
    DEMO_MATLIST_CSV_PATH = os.environ.get('DEMO_MATLIST_CSV_PATH', 'data/sample_product_data.csv')
    DEMO_EBAY_CONFIG_JSON_PATH = os.environ.get('DEMO_EBAY_CONFIG_JSON_PATH', 'data/ebay_tokens_demo.json')

    # Flask session configuration.
    # We use the file system to make it persistent.
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24) # Sessions last 24 hours.
    SESSION_USE_SIGNER = False # Temporarily disable signing to avoid bytes/string issues
    SESSION_KEY_PREFIX = 'ebay_session:'
    SESSION_FILE_DIR = os.environ.get('FLASK_SESSION_DIR', 'data/sessions')
    SESSION_FILE_THRESHOLD = 500
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    # Paths to persistent directories.
    # It's recommended that in production, these paths point to a mounted volume.
    # In create_app, we ensure these directories exist.
    LOG_DIR = os.path.abspath(os.environ.get('LOG_DIR', 'data/logs'))
    OUTPUT_DIR = os.path.abspath(os.environ.get('OUTPUT_DIR', 'data/output'))
    FLASK_SESSION_DIR = os.path.abspath(os.environ.get('FLASK_SESSION_DIR', 'data/sessions'))
    PROCESS_STORE_DIR = os.path.abspath(os.environ.get('PROCESS_STORE_DIR', 'data/processes'))
    
    # Paths to reference data files.
    # Dynamic paths based on demo mode
    if DEMO_MODE:
        MATLIST_CSV_PATH = os.environ.get('MATLIST_CSV_PATH', DEMO_MATLIST_CSV_PATH)
        EBAY_CONFIG_JSON_PATH = os.environ.get('EBAY_CONFIG_JSON_PATH', DEMO_EBAY_CONFIG_JSON_PATH)
    else:
        MATLIST_CSV_PATH = os.environ.get('MATLIST_CSV_PATH', 'data/ktypemaster3.csv')
        EBAY_CONFIG_JSON_PATH = os.environ.get('EBAY_CONFIG_JSON_PATH', 'data/ebay_tokens.json')

    # eBay API credentials.
    EBAY_APP_ID = os.environ.get('EBAY_APP_ID')
    EBAY_CERT_ID = os.environ.get('EBAY_CERT_ID')
    EBAY_DEV_ID = os.environ.get('EBAY_DEV_ID')

    # Store configuration.
    # Initials used for naming files.
    STORE_INITIALS = {
        'carmatsking_uk': 'MK',
        'car_mats_custom': 'CC',
        'vwcarmatsuk': 'VW',
        'custom-fit-car-mats': 'CF',
        'car-mats-to-fit': 'CM',
        # Demo stores for demo mode
        'demo_store_1': 'DS1',
        'demo_store_2': 'DS2',
        'demo_store_3': 'DS3',
        # Add more stores here if needed
    }

    # Store accounts with their refresh tokens.
    # The format is a list of dictionaries. Loaded dynamically.
    # The loop will look for EBAY_STORE_1_ID, EBAY_STORE_1_REFRESH_TOKEN, etc.
    # in the .env file until it finds no more.
    EBAY_STORE_ACCOUNTS = []
    if not DEMO_MODE:
        # Real store accounts (only load in production mode)
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
    else:
        # Demo store accounts
        EBAY_STORE_ACCOUNTS = [
            {'account_id': 'demo_store_1', 'refresh_token': 'demo_refresh_token_1'},
            {'account_id': 'demo_store_2', 'refresh_token': 'demo_refresh_token_2'},
            {'account_id': 'demo_store_3', 'refresh_token': 'demo_refresh_token_3'}
        ]

    # Task scheduler configuration.
    ENABLE_SCHEDULER = os.environ.get('ENABLE_SCHEDULER', 'True').lower() == 'true'
    SESSION_LIFETIME_HOURS = 24
    SESSION_CLEANUP_INTERVAL_HOURS = 6
    PROCESS_FILE_RETENTION_HOURS = 48
    PROCESS_CLEANUP_INTERVAL_HOURS = 12
    
    # Processing parameters
    DEFAULT_ORDER_FETCH_DAYS = 29