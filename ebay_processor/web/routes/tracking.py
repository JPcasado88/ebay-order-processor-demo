# ebay_processor/web/routes/tracking.py
"""
Rutas para la Carga de Archivos de Tracking.

Este módulo gestiona la subida de archivos CSV de las transportadoras
con los números de seguimiento y actualiza los archivos de tracking
generados por la aplicación.
"""

import logging
import os
import shutil
import random
import glob
from datetime import datetime, timezone

import pandas as pd
import openpyxl
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
from werkzeug.utils import secure_filename

from ..decorators import login_required
from ...core.constants import INFO_HEADER_TAG

logger = logging.getLogger(__name__)

# Creamos el Blueprint para las rutas de tracking.
tracking_bp = Blueprint(
    'tracking',
    __name__,
    template_folder='../../templates',
    static_folder='../../static'
)


@tracking_bp.route('/upload-tracking', methods=['GET'])
@login_required
def upload_tracking_form():
    """Muestra el formulario para subir el archivo de tracking."""
    output_dir = current_app.config['OUTPUT_DIR']
    
    # Busca archivos de tracking existentes para mostrarlos en el formulario.
    try:
        tracking_pattern = os.path.join(output_dir, '*Tracking*.xlsx')
        # Usamos una comprensión de generador para eficiencia
        tracking_files = (os.path.basename(f) for f in glob.glob(tracking_pattern) if os.path.isfile(f))
        # Ordenamos la lista final
        sorted_files = sorted(list(tracking_files))
        
        # Also look for demo CSV files for automatic suggestion
        csv_pattern = os.path.join(output_dir, '*COURIER_UPLOAD_DEMO.csv')
        demo_csv_files = sorted([os.path.basename(f) for f in glob.glob(csv_pattern) if os.path.isfile(f)])
        
        # Find the most recent consolidated CSV for demo suggestion
        consolidated_csv = None
        for csv_file in reversed(demo_csv_files):  # Most recent first due to timestamp
            if 'CONSOLIDATED' in csv_file:
                consolidated_csv = csv_file
                break
                
    except Exception as e:
        logger.error(f"Error al listar archivos de tracking: {e}", exc_info=True)
        flash("No se pudo obtener la lista de archivos de tracking existentes.", "error")
        sorted_files = []
        demo_csv_files = []
        consolidated_csv = None
        
    return render_template('upload_tracking.html', 
                         existing_files=sorted_files,
                         demo_csv_files=demo_csv_files,
                         suggested_csv=consolidated_csv)


@tracking_bp.route('/process-tracking-upload', methods=['POST'])
@login_required
def process_tracking_upload():
    """
    Procesa el archivo de tracking subido y actualiza los archivos Excel correspondientes.
    """
    # --- 1. Validación del Archivo de Tracking Subido ---
    # Check if using demo CSV selection
    selected_demo_csv = request.form.get('selected_demo_csv', '').strip()
    
    if selected_demo_csv:
        # Using demo CSV file
        output_dir = current_app.config['OUTPUT_DIR']
        tracking_file_path = os.path.join(output_dir, selected_demo_csv)
        
        if not os.path.exists(tracking_file_path):
            flash(f'El archivo demo seleccionado no existe: {selected_demo_csv}', 'error')
            return redirect(url_for('tracking.upload_tracking_form'))
            
        logger.info(f"Using demo CSV file: {selected_demo_csv}")
        
        # Skip file upload processing, use the existing demo file
        temp_dir = None  # No temp dir needed for demo files
        
    else:
        # Regular file upload
        if 'tracking_file' not in request.files:
            flash('No se encontró el archivo de tracking en la petición.', 'error')
            return redirect(url_for('tracking.upload_tracking_form'))

        tracking_file = request.files['tracking_file']
        if tracking_file.filename == '':
            flash('No se seleccionó ningún archivo de tracking.', 'error')
            return redirect(url_for('tracking.upload_tracking_form'))

        if not tracking_file.filename.lower().endswith('.csv'):
            flash('El archivo de tracking debe ser un fichero CSV.', 'error')
            return redirect(url_for('tracking.upload_tracking_form'))
            
        # --- 2. Crear un Directorio Temporal para la Operación ---
        temp_dir = os.path.join(current_app.config['OUTPUT_DIR'], f"temp_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        os.makedirs(temp_dir, exist_ok=True)
        tracking_file_path = os.path.join(temp_dir, secure_filename(tracking_file.filename))
        tracking_file.save(tracking_file_path)

    # --- 3. Leer y Procesar el CSV de Tracking ---
    try:
        # Intentar leer con varias codificaciones comunes.
        tracking_df = None
        for enc in ['utf-8', 'cp1252', 'latin1']:
            try:
                tracking_df = pd.read_csv(tracking_file_path, encoding=enc)
                logger.info(f"Archivo de tracking leído con codificación: {enc}")
                break
            except UnicodeDecodeError:
                continue
        
        if tracking_df is None:
            raise ValueError("No se pudo decodificar el archivo CSV. Por favor, asegúrate de que esté en formato UTF-8, CP1252 o Latin-1.")

        tracking_df.columns = map(str.lower, tracking_df.columns)
        if 'order number' not in tracking_df.columns or 'consignment number' not in tracking_df.columns:
            raise ValueError("El archivo CSV debe contener las columnas 'Order Number' y 'Consignment Number'.")

        # Crear un mapa de Barcode -> Tracking Number.
        tracking_map = {
            str(row['order number']).strip(): str(row['consignment number']).strip()
            for _, row in tracking_df.iterrows()
            if pd.notna(row['order number']) and pd.notna(row['consignment number'])
        }
        logger.info(f"Mapa de tracking creado con {len(tracking_map)} entradas.")

    except (ValueError, Exception) as e:
        flash(f"Error al procesar el archivo CSV de tracking: {e}", 'error')
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return redirect(url_for('tracking.upload_tracking_form'))

    # --- 4. Procesar los Archivos Excel de Destino ---
    selected_files = request.form.getlist('selected_files')
    update_all = request.form.get('update_all') == 'on'
    
    # If "update all" is checked, get all available tracking files
    if update_all and not selected_files:
        output_dir = current_app.config['OUTPUT_DIR']
        try:
            tracking_pattern = os.path.join(output_dir, '*Tracking*.xlsx')
            all_tracking_files = [os.path.basename(f) for f in glob.glob(tracking_pattern) if os.path.isfile(f)]
            selected_files = sorted(all_tracking_files)
            logger.info(f"Update all selected - processing {len(selected_files)} files: {selected_files}")
        except Exception as e:
            logger.error(f"Error getting tracking files for update all: {e}", exc_info=True)
    
    if not selected_files:
        flash('No se seleccionaron archivos Excel para actualizar.', 'warning')
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return redirect(url_for('tracking.upload_tracking_form'))

    updated_files_info = []
    total_updates = 0
    output_dir = current_app.config['OUTPUT_DIR']

    try:
        for filename in selected_files:
            safe_filename = secure_filename(filename)
            file_path = os.path.join(output_dir, safe_filename)
            
            if not os.path.isfile(file_path):
                flash(f"El archivo '{safe_filename}' no fue encontrado. Omitiendo.", 'warning')
                continue

            try:
                updates_in_file, new_file_path = _update_excel_file(file_path, tracking_map, output_dir, session.get('user_id', 'user'))
                if updates_in_file > 0:
                    updated_files_info.append({
                        'original_file': safe_filename,
                        'updated_file': os.path.basename(new_file_path),
                        'updates': updates_in_file,
                    })
                    total_updates += updates_in_file
                else:
                    flash(f"No se encontraron coincidencias de códigos de barras en el archivo '{safe_filename}'.", 'info')
            except Exception as e:
                logger.error(f"Fallo al actualizar el archivo Excel '{safe_filename}': {e}", exc_info=True)
                flash(f"Ocurrió un error al procesar el archivo '{safe_filename}': {e}", 'error')

        # --- 5. Mostrar Resultados ---
        flash(f'Proceso completado. Se actualizaron {total_updates} números de seguimiento en {len(updated_files_info)} archivo(s).', 'success')
        return render_template('tracking_upload_results.html', updated_files=updated_files_info, total_updates=total_updates)

    finally:
        # --- 6. Limpieza del Directorio Temporal ---
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Directorio temporal de subida de tracking eliminado: {temp_dir}")


def _update_excel_file(original_path: str, tracking_map: dict, output_dir: str, username: str) -> tuple[int, str]:
    """Función de ayuda para actualizar un único archivo Excel."""
    wb = openpyxl.load_workbook(original_path)
    ws = wb.active # Suponemos que los datos están en la primera hoja activa.

    # Determinar la fila de la cabecera.
    header_row_index = 2 if ws.cell(row=1, column=1).value == INFO_HEADER_TAG else 1
    headers = {str(cell.value).lower().strip(): idx for idx, cell in enumerate(ws[header_row_index], 1) if cell.value}
    
    barcode_col = headers.get('our_barcode')
    tracking_col = headers.get('tracking number')

    if not barcode_col or not tracking_col:
        raise ValueError("El archivo Excel no contiene las columnas 'Our_Barcode' o 'Tracking Number'.")

    updates = 0
    for row in range(header_row_index + 1, ws.max_row + 1):
        barcode_cell = ws.cell(row=row, column=barcode_col)
        barcode_value = str(barcode_cell.value).strip() if barcode_cell.value else None
        
        if barcode_value in tracking_map:
            tracking_number = tracking_map[barcode_value]
            tracking_cell = ws.cell(row=row, column=tracking_col)
            tracking_cell.value = tracking_number
            tracking_cell.number_format = '@' # Asegurar que se guarde como texto.
            updates += 1
    
    if updates > 0:
        base, ext = os.path.splitext(os.path.basename(original_path))
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')
        new_filename = f"{base}_updated_{username}_{timestamp}{ext}"
        new_path = os.path.join(output_dir, new_filename)
        wb.save(new_path)
        return updates, new_path
    
    return 0, ""