# ebay_processor/web/routes/auth.py
"""
Authentication Routes.

This module handles user login and logout.
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

# Import custom exceptions for clearer error handling.
from ...core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Create a Blueprint. This is like a "mini-server" in Flask that we'll
# register in the main application. It's the standard way to organize routes.
auth_bp = Blueprint(
    'auth',
    __name__,
    template_folder='../../templates',  # Tell it where to find templates
    static_folder='../../static'       # and static files.
)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    # If the user is already logged in, redirect them to the main page.
    if 'user_id' in session:
        return redirect(url_for('processing.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Please enter username and password.', 'warning')
            return render_template('login.html')

        try:
            # Get credentials from the app configuration.
            # current_app is a Flask proxy that points to the current application.
            stored_username = current_app.config.get('ADMIN_USERNAME')
            stored_hash = current_app.config.get('ADMIN_PASSWORD_HASH')

            if not stored_username or not stored_hash:
                raise ConfigurationError("Administrator credentials are not configured in the environment.")

            # Compare username and password hash.
            if username == stored_username and check_password_hash(stored_hash, password):
                session.clear()  # Clear any previous session.
                session['user_id'] = username  # Use 'user_id' as standard.
                
                logger.info(f"Successful login for user '{username}'.")
                flash('You have logged in successfully!', 'success')
                
                # Redirect to processing page (using the 'processing' blueprint name).
                return redirect(url_for('processing.index'))
            else:
                logger.warning(f"Failed login attempt for user '{username}'.")
                flash('Incorrect username or password.', 'error')

        except ConfigurationError as e:
            logger.critical(f"Configuration error during login: {e}")
            flash('The application is not configured correctly. Contact the administrator.', 'danger')
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}", exc_info=True)
            flash('An unexpected error occurred. Please try again.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Handles user logout."""
    username = session.pop('user_id', None)
    session.clear()  # Clear the entire session to ensure complete logout.

    if username:
        logger.info(f"User '{username}' has logged out.")
    
    flash('You have logged out.', 'info')
    return redirect(url_for('auth.login')) # Redirect to login page.