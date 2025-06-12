# ebay_processor/web/decorators.py
"""
Custom Flask Decorators Module.

This file contains decorators that can be applied to view functions (routes)
to add cross-cutting functionality, such as authentication checking.
"""
from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    """
    Decorator that verifies if a user has logged in.

    If the user is not in the session (identified by the presence of 'user_id'),
    redirects them to the login page.

    This decorator should be applied to all routes that require
    the user to be authenticated.

    Usage:
        @app.route('/secret-page')
        @login_required
        def secret_page():
            return "Only for logged-in users."
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # The 'user_id' key is what we set in the successful login route.
        if 'user_id' not in session:
            # If not found, show a message and redirect.
            flash('Please log in to access this page.', 'warning')
            
            # Use url_for('auth.login') to point to the 'login' function
            # within the 'auth' Blueprint.
            return redirect(url_for('auth.login'))
        
        # If the user is in the session, the original function (the route) executes.
        return f(*args, **kwargs)
    
    return decorated_function