# ebay_processor/web/routes/processing.py
"""
Rutas de Procesamiento de Pedidos.

Este módulo contiene las rutas para la funcionalidad principal de la aplicación:
- La página de inicio para configurar y lanzar un nuevo proceso.
- El endpoint para iniciar el trabajo en segundo plano de forma asíncrona.
- La página de progreso que consulta el estado del trabajo.
- La página de resultados finales.
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

# Importamos el decorador de login y las dependencias de servicio
from ..decorators import login_required
from ...services.order_processing import start_order_processing_thread
from ...persistence.process_store import ProcessStore

logger = logging.getLogger(__name__)

# Creamos el Blueprint para las rutas de procesamiento
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
    Muestra la página principal de la aplicación, donde el usuario
    puede configurar y iniciar un nuevo proceso de obtención de pedidos.
    """
    return render_template('index.html')


@processing_bp.route('/process/start', methods=['POST'])
@login_required
def start_process():
    """
    Endpoint API para iniciar un nuevo proceso de fondo.
    Recoge los datos del formulario, crea un registro de proceso inicial,
    y lanza el hilo que hará el trabajo pesado.
    """
    try:
        # 1. Recopilar datos del formulario.
        form_data = {
            'output_files': request.form.getlist('output_files'),
            'include_all_orders': 'include_all_orders' in request.form,
            'from_date_str': request.form.get('from_date', ''),
            'next_24h_only': 'next_24h_only' in request.form,
        }

        if not form_data['output_files']:
            return jsonify({'status': 'error', 'message': 'Debes seleccionar al menos un tipo de archivo a generar.'}), 400

        # --- LÓGICA DE FECHA CORREGIDA ---
        # Determinar el objeto datetime de inicio (from_dt) aquí, en la capa web.
        from_dt = None
        from_date_input = form_data.get('from_date_str')
        
        if from_date_input:
            # El input de fecha de HTML viene como 'YYYY-MM-DD'.
            # Lo convertimos a un objeto datetime, poniéndolo al inicio del día (medianoche).
            from_dt = datetime.strptime(from_date_input, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            # Si no se proporciona fecha, usamos el valor por defecto de la configuración.
            default_days = current_app.config.get('DEFAULT_ORDER_FETCH_DAYS', 29)
            from_dt = datetime.now(timezone.utc) - timedelta(days=default_days)
        
        # 2. Crear un ID de proceso único y un directorio temporal.
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
        process_id = f"proc_{timestamp}_{random.randint(1000, 9999)}"
        batch_id = f"batch_{timestamp}"
        temp_dir = os.path.join(current_app.config['OUTPUT_DIR'], 'temp_batches', batch_id)
        os.makedirs(temp_dir, exist_ok=True)

        # 3. Crear el registro de estado inicial para el proceso.
        process_store = ProcessStore(current_app.config['PROCESS_STORE_DIR'])
        initial_info = {
            'process_id': process_id,
            'user': session.get('user_id', 'Unknown'),
            'form_data': form_data,
            'temp_dir': temp_dir,
            'batch_id': batch_id,
            'status': 'initializing',
            'progress': 0,
            'message': 'Inicializando proceso...',
            'start_time_iso': datetime.now(timezone.utc).isoformat(),
            'completion_time_iso': None,
            'generated_files': [],
            'generated_file_paths': {},
            'zip_file': None,
            # Guardamos la fecha SIEMPRE como un string en formato ISO.
            'from_dt_iso': from_dt.isoformat() 
        }
        process_store.update(process_id, initial_info)
        
        # 4. Lanzar el hilo de fondo.
        app_context = current_app._get_current_object()
        thread = threading.Thread(
            target=start_order_processing_thread,
            args=(app_context, process_id),
            name=f"ProcessThread-{process_id}"
        )
        thread.daemon = True
        thread.start()

        logger.info(f"Proceso en segundo plano iniciado por el usuario '{session.get('user_id')}' con ID: {process_id}")
        
        # 5. Devolver una respuesta JSON con el ID del proceso para que el frontend pueda redirigir.
        return jsonify({
            'status': 'started',
            'process_id': process_id,
            'redirect_url': url_for('processing.show_progress', process_id=process_id)
        })

    except Exception as e:
        logger.error(f"Error al iniciar el proceso: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Error inesperado del servidor: {e}'}), 500

@processing_bp.route('/process/progress/<process_id>')
@login_required
def show_progress(process_id: str):
    """
    Muestra la página de "procesando..." que hará polling para obtener el estado.
    """
    process_store = ProcessStore(current_app.config['PROCESS_STORE_DIR'])
    info = process_store.get(process_id)
    if not info:
        flash("El proceso solicitado no fue encontrado o ha expirado.", "warning")
        return redirect(url_for('processing.index'))
    
    # Si el proceso ya está completo, redirigir directamente a los resultados.
    if info.get('status') in ['complete', 'error']:
        return redirect(url_for('processing.show_results', process_id=process_id))

    return render_template('processing.html', process_id=process_id)


@processing_bp.route('/process/status/<process_id>')
@login_required
def get_status(process_id: str):
    """
    Endpoint API para que el frontend consulte el estado actual de un proceso.
    """
    process_store = ProcessStore(current_app.config['PROCESS_STORE_DIR'])
    info = process_store.get(process_id)

    if not info:
        return jsonify({'status': 'not_found', 'message': 'Proceso no encontrado.'}), 404

    # Devolvemos solo la información necesaria para la interfaz de usuario.
    response_data = {
        'status': info.get('status', 'unknown'),
        'progress': info.get('progress', 0),
        'message': info.get('message', ''),
        'store_progress': info.get('store_progress', {}),
    }
    
    # Si el proceso ha terminado, incluimos la URL de la página de resultados y archivos generados.
    if response_data['status'] in ['complete', 'error']:
        response_data['result_url'] = url_for('processing.show_results', process_id=process_id)
        response_data['generated_files'] = info.get('generated_files', [])

    return jsonify(response_data)


@processing_bp.route('/process/results/<process_id>')
@login_required
def show_results(process_id: str):
    """
    Muestra la página de resultados de un proceso completado o fallido.
    """
    process_store = ProcessStore(current_app.config['PROCESS_STORE_DIR'])
    info = process_store.get(process_id)
    
    if not info:
        flash("Los datos del proceso no fueron encontrados. Puede que hayan expirado.", "error")
        return redirect(url_for('processing.index'))

    # Si el proceso aún está en curso, redirigir a la página de progreso.
    if info.get('status') not in ['complete', 'error']:
        flash("El proceso aún no ha finalizado. Por favor, espera.", "warning")
        return redirect(url_for('processing.show_progress', process_id=process_id))
    
    if info.get('status') == 'error':
        flash(f"El proceso finalizó con un error: {info.get('message', 'Error desconocido')}", 'error')

    # Guardar en la sesión solo los archivos que realmente existen
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
    flash('Estado temporal limpiado.', 'info')
    return redirect(url_for('processing.index'))