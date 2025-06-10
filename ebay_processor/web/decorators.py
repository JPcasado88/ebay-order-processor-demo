# ebay_processor/web/decorators.py
"""
Módulo de Decoradores Personalizados de Flask.

Este archivo contiene decoradores que se pueden aplicar a las funciones de vista (rutas)
para añadir funcionalidades transversales, como la comprobación de autenticación.
"""
from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    """
    Decorador que verifica si un usuario ha iniciado sesión.

    Si el usuario no está en la sesión (identificado por la presencia de 'user_id'),
    lo redirige a la página de inicio de sesión.

    Este decorador debe aplicarse a todas las rutas que requieran
    que el usuario esté autenticado.

    Uso:
        @app.route('/secret-page')
        @login_required
        def secret_page():
            return "Solo para usuarios logueados."
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # La clave 'user_id' es la que establecemos en la ruta de login exitoso.
        if 'user_id' not in session:
            # Si no se encuentra, mostramos un mensaje y redirigimos.
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            
            # Usamos url_for('auth.login') para apuntar a la función 'login'
            # dentro del Blueprint 'auth'.
            return redirect(url_for('auth.login'))
        
        # Si el usuario está en la sesión, la función original (la ruta) se ejecuta.
        return f(*args, **kwargs)
    
    return decorated_function