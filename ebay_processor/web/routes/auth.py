# ebay_processor/web/routes/auth.py
"""
Rutas de Autenticación.

Este módulo maneja el login y el logout de los usuarios.
"""
import logging
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
)
from werkzeug.security import check_password_hash

# Importamos las excepciones personalizadas para un manejo de errores más claro.
from ...core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Creamos un Blueprint. Esto es como un "mini-servidor" de Flask que luego
# registraremos en la aplicación principal. Es la forma estándar de organizar rutas.
auth_bp = Blueprint(
    'auth',
    __name__,
    template_folder='../../templates',  # Le decimos dónde encontrar los templates
    static_folder='../../static'       # y los archivos estáticos.
)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Maneja el inicio de sesión del usuario."""
    # Si el usuario ya está logueado, lo redirigimos a la página principal.
    if 'user_id' in session:
        return redirect(url_for('processing.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Por favor, introduce el usuario y la contraseña.', 'warning')
            return render_template('login.html')

        try:
            # Obtenemos las credenciales desde la configuración de la app.
            # current_app es un proxy de Flask que apunta a la aplicación actual.
            stored_username = current_app.config.get('ADMIN_USERNAME')
            stored_hash = current_app.config.get('ADMIN_PASSWORD_HASH')

            if not stored_username or not stored_hash:
                raise ConfigurationError("Las credenciales de administrador no están configuradas en el entorno.")

            # Comparamos el usuario y el hash de la contraseña.
            if username == stored_username and check_password_hash(stored_hash, password):
                session.clear()  # Limpiar cualquier sesión anterior.
                session['user_id'] = username  # Usamos 'user_id' como estándar.
                
                logger.info(f"Inicio de sesión exitoso para el usuario '{username}'.")
                flash('¡Has iniciado sesión correctamente!', 'success')
                
                # Redirigir a la página de procesamiento (usando el nombre del blueprint 'processing').
                return redirect(url_for('processing.index'))
            else:
                logger.warning(f"Intento de inicio de sesión fallido para el usuario '{username}'.")
                flash('Usuario o contraseña incorrectos.', 'error')

        except ConfigurationError as e:
            logger.critical(f"Error de configuración durante el login: {e}")
            flash('La aplicación no está configurada correctamente. Contacta al administrador.', 'danger')
        except Exception as e:
            logger.error(f"Error inesperado durante el login: {e}", exc_info=True)
            flash('Ocurrió un error inesperado. Inténtalo de nuevo.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Maneja el cierre de sesión del usuario."""
    username = session.pop('user_id', None)
    session.clear()  # Limpia toda la sesión para asegurar un logout completo.

    if username:
        logger.info(f"El usuario '{username}' ha cerrado sesión.")
    
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('auth.login')) # Redirige a la página de login.