# ebay_processor/web/routes/health.py
"""
Ruta para la comprobación de estado (health check).
"""
from flask import Blueprint

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """
    Endpoint simple para que las plataformas de despliegue (como Railway)
    puedan verificar que la aplicación está en funcionamiento.
    """
    return "OK", 200