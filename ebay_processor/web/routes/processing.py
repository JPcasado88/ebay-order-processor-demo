# ebay_processor/web/routes/processing.py
"""
Order Processing Routes.

This module contains routes for the main functionality of the application:
- The home page to configure and launch a new process.
- The endpoint to start background work asynchronously.
- The progress page that polls for work status.
- The final results page.
"""

import logging
import os
from datetime import datetime, timezone, timedelta
import random
import threading

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    current_app,
)

# Import login decorator and service dependencies
from ..decorators import login_required
from ...services.order_processing import start_order_processing_thread
from ...persistence.process_store import ProcessStore

logger = logging.getLogger(__name__)

# Create the Blueprint for processing routes
processing_bp = Blueprint(
    'processing',
    __name__,
    template_folder='../../templates',
    static_folder='../../static'
)


@processing_bp.route('/')
@login_required
def index():
    """
    Shows the main page of the application, where the user
    can configure and start a new order retrieval process.
    """
    return render_template('index.html')


@processing_bp.route('/process/start', methods=['POST'])
@login_required
def start_process():
    """
    API endpoint to start a new background process.
    Collects form data, creates an initial process record,
    and launches the thread that will do the heavy work.
    """
    try:
        # 1. Collect form data.
        form_data = {
            'output_files': request.form.getlist('output_files'),
            'include_all_orders': 'include_all_orders' in request.form,
            'from_date_str': request.form.get('from_date', ''),
            'next_24h_only': 'next_24h_only' in request.form,
        }

        if not form_data['output_files']:
            return jsonify({'status': 'error', 'message': 'You must select at least one file type to generate.'}), 400

        # --- CORRECTED DATE LOGIC ---
        # Determine the start datetime object (from_dt) here, in the web layer.
        from_dt = None
        from_date_input = form_data.get('from_date_str')
        
        if from_date_input:
            # HTML date input comes as 'YYYY-MM-DD'.
            # Convert it to a datetime object, setting it to start of day (midnight).
            from_dt = datetime.strptime(from_date_input, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            # If no date is provided, use the default value from configuration.
            default_days = current_app.config.get('DEFAULT_ORDER_FETCH_DAYS', 29)
            from_dt = datetime.now(timezone.utc) - timedelta(days=default_days)
        
        # 2. Create a unique process ID and temporary directory.
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
        process_id = f"proc_{timestamp}_{random.randint(1000, 9999)}"
        batch_id = f"batch_{timestamp}"
        temp_dir = os.path.join(current_app.config['OUTPUT_DIR'], 'temp_batches', batch_id)
        os.makedirs(temp_dir, exist_ok=True)

        # 3. Create the initial status record for the process.
        process_store = ProcessStore(current_app.config['PROCESS_STORE_DIR'])
        initial_info = {
            'process_id': process_id,
            'user': session.get('user_id', 'Unknown'),
            'form_data': form_data,
            'temp_dir': temp_dir,
            'batch_id': batch_id,
            'status': 'initializing',
            'progress': 0,
            'message': 'Initializing process...',
            'start_time_iso': datetime.now(timezone.utc).isoformat(),
            'completion_time_iso': None,
            'generated_files': [],
            'generated_file_paths': {},
            'zip_file': None,
            # Always save the date as an ISO format string.
            'from_dt_iso': from_dt.isoformat() 
        }
        process_store.update(process_id, initial_info)
        
        # 4. Launch the background thread.
        app_context = current_app._get_current_object()
        thread = threading.Thread(
            target=start_order_processing_thread,
            args=(app_context, process_id),
            name=f"ProcessThread-{process_id}"
        )
        thread.daemon = True
        thread.start()

        logger.info(f"Background process started by user '{session.get('user_id')}' with ID: {process_id}")
        
        # 5. Return a JSON response with the process ID so the frontend can redirect.
        return jsonify({
            'status': 'started',
            'process_id': process_id,
            'redirect_url': url_for('processing.show_progress', process_id=process_id)
        })

    except Exception as e:
        logger.error(f"Error starting process: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Unexpected server error: {e}'}), 500

@processing_bp.route('/process/progress/<process_id>')
@login_required
def show_progress(process_id: str):
    """
    Shows the "processing..." page that will poll for status.
    """
    process_store = ProcessStore(current_app.config['PROCESS_STORE_DIR'])
    info = process_store.get(process_id)
    if not info:
        flash("The requested process was not found or has expired.", "warning")
        return redirect(url_for('processing.index'))
    
    # If the process is already complete, redirect directly to results.
    if info.get('status') in ['complete', 'error']:
        return redirect(url_for('processing.show_results', process_id=process_id))

    return render_template('processing.html', process_id=process_id)


@processing_bp.route('/process/status/<process_id>')
@login_required
def get_status(process_id: str):
    """
    API endpoint for the frontend to query the current status of a process.
    """
    process_store = ProcessStore(current_app.config['PROCESS_STORE_DIR'])
    info = process_store.get(process_id)

    if not info:
        return jsonify({'status': 'not_found', 'message': 'Process not found.'}), 404

    # Return only the information needed for the user interface.
    response_data = {
        'status': info.get('status', 'unknown'),
        'progress': info.get('progress', 0),
        'message': info.get('message', ''),
        'store_progress': info.get('store_progress', {}),
    }
    
    # If the process has finished, include the results page URL and generated files.
    if response_data['status'] in ['complete', 'error']:
        response_data['result_url'] = url_for('processing.show_results', process_id=process_id)
        response_data['generated_files'] = info.get('generated_files', [])

    return jsonify(response_data)


@processing_bp.route('/process/results/<process_id>')
@login_required
def show_results(process_id: str):
    """
    Shows the results page of a completed or failed process.
    """
    process_store = ProcessStore(current_app.config['PROCESS_STORE_DIR'])
    info = process_store.get(process_id)
    
    if not info:
        flash("Process data was not found. It may have expired.", "error")
        return redirect(url_for('processing.index'))

    # If the process is still in progress, redirect to progress page.
    if info.get('status') not in ['complete', 'error']:
        flash("The process has not finished yet. Please wait.", "warning")
        return redirect(url_for('processing.show_progress', process_id=process_id))
    
    if info.get('status') == 'error':
        flash(f"The process finished with an error: {info.get('message', 'Unknown error')}", 'error')

    # Save to session only files that actually exist
    all_file_paths = info.get('generated_file_paths', {})
    existing_file_paths = {name: path for name, path in all_file_paths.items() if os.path.exists(path)}
    
    session['generated_files'] = existing_file_paths
    session['zip_file_path'] = info.get('zip_file', {}).get('path')

    return render_template('results.html', results=info, process_id=process_id)


# Additional routes that templates reference
@processing_bp.route('/process/async', methods=['POST'])
@login_required
def process_async():
    """Alias for start_process for backward compatibility."""
    return start_process()


@processing_bp.route('/process/status/<process_id>')  
@login_required
def process_status(process_id: str):
    """Alias for get_status for backward compatibility."""
    return get_status(process_id)


@processing_bp.route('/clear-temporary-state', methods=['POST'])
@login_required  
def clear_temporary_state():
    """Clear temporary session state."""
    session.pop('generated_files', None)
    session.pop('zip_file_path', None)
    flash('Temporary state cleared.', 'info')
    return redirect(url_for('processing.index'))