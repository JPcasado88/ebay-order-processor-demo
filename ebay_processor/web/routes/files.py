# ebay_processor/web/routes/files.py
"""
Rutas para la Gestión de Archivos.

Este módulo maneja todas las interacciones del usuario con los archivos generados:
- Descarga de archivos individuales.
- Descarga del archivo ZIP consolidado.
- Visualización y eliminación de archivos en el servidor.
"""

import logging
import os
import glob
from datetime import datetime

from flask import (
    Blueprint,
    redirect,
    url_for,
    flash,
    session,
    send_file,
    current_app,
    render_template,
    request,
)
from werkzeug.utils import secure_filename

from ..decorators import login_required

logger = logging.getLogger(__name__)

# Creamos el Blueprint para las rutas de archivos.
files_bp = Blueprint(
    'files',
    __name__,
    template_folder='../../templates',
    static_folder='../../static'
)


@files_bp.route('/download/file/<path:filename>')
@login_required
def download_single_file(filename: str):
    """
    Descarga un archivo específico generado por un proceso.
    El nombre del archivo se obtiene de la sesión para mayor seguridad.
    """
    # Usamos werkzeug.utils.secure_filename para sanear el nombre del archivo.
    safe_filename = secure_filename(filename)

    # Obtenemos la ruta completa del archivo desde la información guardada en la sesión.
    file_paths = session.get('generated_files', {})
    file_path = file_paths.get(safe_filename)

    if not file_path:
        logger.error(f"Archivo no encontrado en sesión: '{safe_filename}' por usuario '{session.get('user_id')}'.")
        flash(f'El archivo "{safe_filename}" no está disponible para descarga. La sesión puede haber expirado.', 'warning')
        return redirect(url_for('processing.index'))
    
    if not os.path.isfile(file_path):
        logger.error(f"Archivo físico no encontrado: '{file_path}' para usuario '{session.get('user_id')}'.")
        flash(f'El archivo "{safe_filename}" no existe en el servidor. Puede haber sido eliminado.', 'danger')
        return redirect(url_for('processing.index'))

    logger.info(f"Usuario '{session.get('user_id')}' descargando archivo: {file_path}")
    
    # send_file se encarga de enviar el archivo al navegador como un adjunto.
    return send_file(file_path, as_attachment=True)


@files_bp.route('/download/zip')
@login_required
def download_zip_archive():
    """Descarga el archivo ZIP que contiene todos los archivos de un proceso."""
    zip_path = session.get('zip_file_path')

    if not zip_path or not os.path.isfile(zip_path):
        logger.error(f"Intento de descarga de archivo ZIP no encontrado por usuario '{session.get('user_id')}'. Ruta esperada: {zip_path}")
        flash('El archivo ZIP para este proceso no fue encontrado o la sesión ha expirado.', 'danger')
        return redirect(request.referrer or url_for('processing.index'))

    logger.info(f"Usuario '{session.get('user_id')}' descargando archivo ZIP: {zip_path}")
    
    return send_file(zip_path, as_attachment=True)


@files_bp.route('/manage-files', methods=['GET', 'POST'])
@login_required
def manage_files():
    """
    Muestra una página para ver todos los archivos generados y permite eliminarlos.
    """
    output_dir = current_app.config['OUTPUT_DIR']

    if request.method == 'POST':
        # Esta es una acción destructiva, la registramos claramente.
        user = session.get('user_id', 'Unknown')
        selected_files = request.form.getlist('selected_files')
        
        if not selected_files:
            flash('No se seleccionó ningún archivo para eliminar.', 'warning')
            return redirect(url_for('files.manage_files'))

        logger.info(f"Usuario '{user}' ha iniciado la eliminación de {len(selected_files)} archivo(s).")
        
        deleted_count, error_count = 0, 0
        for filename in selected_files:
            # Sanear cada nombre de archivo por seguridad.
            safe_filename = secure_filename(filename)
            file_path = os.path.join(output_dir, safe_filename)
            
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                else:
                    logger.warning(f"El archivo a eliminar no fue encontrado (quizás ya borrado): {file_path}")
                    error_count += 1
            except Exception as e:
                logger.error(f"Error al eliminar el archivo {file_path}: {e}", exc_info=True)
                error_count += 1
        
        flash_message = f'Se eliminaron {deleted_count} archivo(s) correctamente.'
        if error_count > 0:
            flash_message += f' Se encontraron {error_count} error(es).'
            flash(flash_message, 'warning')
        else:
            flash(flash_message, 'success')
            
        return redirect(url_for('files.manage_files'))

    # Lógica para la petición GET: listar todos los archivos.
    files_list = []
    try:
        # Buscamos solo los tipos de archivo que genera nuestra aplicación.
        file_patterns = ['*.xlsx', '*.csv', '*.zip']
        for pattern in file_patterns:
            for file_path in glob.glob(os.path.join(output_dir, pattern)):
                try:
                    stat = os.stat(file_path)
                    files_list.append({
                        'name': os.path.basename(file_path),
                        'size_kb': round(stat.st_size / 1024, 2),
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                    })
                except OSError:
                    # Puede ocurrir si el archivo se elimina mientras se lista.
                    continue
    except Exception as e:
        logger.error(f"Error al listar el directorio de salida '{output_dir}': {e}", exc_info=True)
        flash('Ocurrió un error al intentar obtener la lista de archivos.', 'error')

    # Ordenar por fecha de modificación, los más nuevos primero.
    files_list.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template('manage_files.html', files=files_list)