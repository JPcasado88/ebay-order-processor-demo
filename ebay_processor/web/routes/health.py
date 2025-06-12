# ebay_processor/web/routes/health.py
"""
Health check route.
"""
from flask import Blueprint

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """
    Simple endpoint for deployment platforms (like Railway)
    to verify that the application is running.
    """
    return "OK", 200