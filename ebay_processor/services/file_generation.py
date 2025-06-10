# ebay_processor/services/file_generation.py
"""
Servicio de Generación de Archivos.

Este módulo es responsable de crear todos los archivos de salida, principalmente
hojas de cálculo de Excel (RUN, COURIER_MASTER, Tracking, etc.).
Toma datos ya procesados y los formatea según las especificaciones de cada archivo.
"""
import logging
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Importamos utilidades y constantes del proyecto
from ..core.constants import (
    HIGHLANDS_AND_ISLANDS_POSTCODES,
    NEXT_DAY_SERVICE_NAME,
    STANDARD_SERVICE_NAME,
    INFO_HEADER_TAG,
    RUN_SHEET_TITLE,
    RUN24H_SHEET_TITLE,
    COURIER_MASTER_SHEET_TITLE,
    TRACKING_SHEET_TITLE,
    UNMATCHED_SHEET_TITLE,
)
from ..core.exceptions import FileGenerationError
from ..utils.string_utils import sanitize_for_excel

logger = logging.getLogger(__name__)


# --- Funciones Públicas de Generación de Archivos ---

def generate_consolidated_run_file(
    orders: List[Dict[str, Any]], output_dir: str, run_date: datetime, config: Dict
) -> Optional[str]:
    """
    Genera un único archivo RUN consolidado para pedidos estándar.

    Args:
        orders: Lista de ítems de pedido estándar.
        output_dir: Directorio donde se guardará el archivo.
        run_date: Fecha de la ejecución para el nombre del archivo.
        config: Diccionario de configuración de la app.

    Returns:
        La ruta al archivo generado o None si no se generó.
    """
    logger.info(f"Generando archivo RUN consolidado para {len(orders)} ítems estándar.")
    if not orders:
        return None

    filename = _generate_filename("RUN", None, run_date, consolidated=True)
    rows = [_format_run_row(item) for item in orders]
    
    return _save_excel_file(rows, output_dir, filename, RUN_SHEET_TITLE, config)


def generate_run24h_file(
    orders: List[Dict[str, Any]], output_dir: str, run_date: datetime, config: Dict
) -> Optional[str]:
    """
    Genera un único archivo RUN24H consolidado para pedidos urgentes/expedited.

    Args:
        orders: Lista de ítems de pedido urgentes.
        output_dir: Directorio donde se guardará el archivo.
        run_date: Fecha de la ejecución para el nombre del archivo.
        config: Diccionario de configuración de la app.

    Returns:
        La ruta al archivo generado o None si no se generó.
    """
    logger.info(f"Generando archivo RUN24H consolidado para {len(orders)} ítems urgentes.")
    if not orders:
        return None

    filename = _generate_filename("RUN24H", None, run_date, consolidated=True)
    rows = [_format_run_row(item) for item in orders]

    return _save_excel_file(rows, output_dir, filename, RUN24H_SHEET_TITLE, config)


def generate_consolidated_courier_master_file(
    all_orders: List[Dict[str, Any]], output_dir: str, run_date: datetime, config: Dict
) -> Optional[str]:
    """
    Genera un único archivo COURIER_MASTER consolidado con una fila por pedido.

    Args:
        all_orders: Lista de todos los ítems procesados.
        output_dir: Directorio donde se guardará el archivo.
        run_date: Fecha de la ejecución para el nombre del archivo.
        config: Diccionario de configuración de la app.

    Returns:
        La ruta al archivo generado o None si no se generó.
    """
    logger.info(f"Generando COURIER_MASTER para un total de {len(all_orders)} ítems.")
    if not all_orders:
        return None
        
    order_groups = _group_items_by_order_id(all_orders)
    rows = []
    for order_id, items in order_groups.items():
        first_item = items[0]
        rows.append(_format_courier_master_row(first_item, items))

    if rows:
        filename = _generate_filename("COURIER_MASTER", None, run_date, consolidated=True, config=config)
        return _save_excel_file(rows, output_dir, filename, COURIER_MASTER_SHEET_TITLE, config)
    return None


def generate_tracking_files(
    all_orders: List[Dict[str, Any]], output_dir: str, run_date: datetime, config: Dict
) -> List[str]:
    """
    Genera múltiples archivos de Tracking: uno consolidado y uno por cada tienda.

    Args:
        all_orders: Lista de todos los ítems procesados.
        output_dir: Directorio donde se guardarán los archivos.
        run_date: Fecha de la ejecución para los nombres de archivo.
        config: Diccionario de configuración de la app.

    Returns:
        Una lista de rutas a los archivos de tracking generados.
    """
    logger.info("Iniciando la generación de todos los archivos de Tracking.")
    generated_paths = []

    # 1. Generar archivo de tracking consolidado.
    consolidated_path = _create_single_tracking_file(
        all_orders, output_dir, run_date, config, is_consolidated=True
    )
    if consolidated_path:
        generated_paths.append(consolidated_path)

    # 2. Generar archivos de tracking por tienda.
    store_groups = _group_items_by_store_id(all_orders)
    for store_id, items in store_groups.items():
        store_path = _create_single_tracking_file(
            items, output_dir, run_date, config, is_consolidated=False, store_id=store_id
        )
        if store_path:
            generated_paths.append(store_path)
            
    return generated_paths


def generate_unmatched_items_file(
    unmatched_items: List[Dict[str, Any]], output_dir: str, run_date: datetime, config: Dict
) -> Optional[str]:
    """
    Genera un archivo Excel con todos los ítems que no pudieron ser emparejados.

    Args:
        unmatched_items: Lista de diccionarios de ítems sin coincidencia.
        output_dir: Directorio donde se guardará el archivo.
        run_date: Fecha de la ejecución para el nombre del archivo.
        config: Diccionario de configuración de la app.

    Returns:
        La ruta al archivo generado o None si no había ítems sin coincidencia.
    """
    logger.info(f"Generando archivo de ítems no encontrados para {len(unmatched_items)} ítems.")
    if not unmatched_items:
        return None
    
    filename = f"unmatched_items_{run_date.strftime('%Y%m%d_%H%M%S')}.xlsx"
    return _save_excel_file(unmatched_items, output_dir, filename, UNMATCHED_SHEET_TITLE, config)


# --- Funciones de Ayuda Privadas (Lógica de Formato y Guardado) ---

def _create_single_tracking_file(
    orders: List[Dict[str, Any]],
    output_dir: str,
    run_date: datetime,
    config: Dict,
    is_consolidated: bool,
    store_id: Optional[str] = None,
) -> Optional[str]:
    """
    Función de ayuda interna para crear un único archivo de tracking.
    """
    if not orders:
        return None

    filename = _generate_filename("Tracking", store_id, run_date, consolidated=is_consolidated, config=config)
    order_groups = _group_items_by_order_id(orders)

    rows = []
    for order_id, items in order_groups.items():
        # Para el archivo de tracking, solo necesitamos una fila por pedido,
        # usando el primer ítem como representativo.
        representative_item = items[0]
        rows.append(_format_tracking_row(representative_item, order_id))
    
    if rows:
        return _save_excel_file(rows, output_dir, filename, TRACKING_SHEET_TITLE, config, has_info_header=True)
    return None

def _format_run_row(item: Dict[str, Any]) -> Dict[str, Any]:
    """Formatea un único ítem para una fila en un archivo RUN."""
    shuffled_add = _shuffle_address(item.get('ADD1'), item.get('ADD2'), item.get('ADD3'), item.get('ADD4'))
    return {
        'FILE NAME': item.get('FILE NAME', ''),
        'Process DATE': item.get('Process DATE', ''),
        'ORIGIN OF ORDER': 'eBay',
        'FIRST NAME': item.get('FIRST NAME', ''),
        'LAST NAME': item.get('LAST NAME', ''),
        'ADD1': shuffled_add[0],
        'ADD2': shuffled_add[1],
        'ADD3': shuffled_add[2],
        'ADD4': shuffled_add[3],
        'POSTCODE': item.get('POSTCODE', ''),
        'TEL NO': item.get('TEL NO', ''),
        'EMAIL ADDRESS': item.get('EMAIL ADDRESS', ''),
        'QTY': '1',  # Un archivo RUN siempre es una fila por ítem.
        'REF NO': str(item.get('REF NO', '')).upper(),
        'TRIM': item.get('TRIM', ''),
        'Thread Colour': 'Matched',
        'Embroidery': item.get('Embroidery', ''),
        'CARPET TYPE': item.get('CARPET TYPE', ''),
        'CARPET COLOUR': item.get('CARPET COLOUR', ''),
        'Width': '',
        'Make': item.get('Make', ''),
        'Model': item.get('Model', ''),
        'YEAR': item.get('YEAR', ''),
        'Pcs/Set': item.get('Pcs/Set', ''),
        'HEEL PAD REQUIRED': 'No',
        'Other Extra': '',
        'NO OF CLIPS': item.get('NO OF CLIPS', ''),
        'CLIP TYPE': str(item.get('CLIP TYPE', '')).upper(),
        'Courier': '',
        'Tracking No': '',
        'Bar Code Type': 'CODE93',
        'Bar Code': item.get('FinalBarcode', ''), # Usar el barcode final asignado por el BarcodeService
        'AF': '',
        'Delivery Special Instruction': item.get('Delivery Special Instruction', ''),
        'Link to Template File': '',
        'Boot Mat 2nd SKU': '',
        'SKU': str(item.get('Raw SKU', '')).upper(),
        'Item Number': str(item.get('Item Number', '')),
        'Transaction ID': str(item.get('Transaction ID', '')),
        'ORDER ID': item.get('ORDER ID', ''),
    }

def _format_courier_master_row(first_item: Dict, all_items_in_order: List) -> Dict:
    """Formatea la fila para el archivo COURIER_MASTER."""
    shuffled_add = _shuffle_address(first_item.get('ADD1'), first_item.get('ADD2'), first_item.get('ADD3'), first_item.get('ADD4'))
    postcode = str(first_item.get('POSTCODE', '')).strip().upper()
    
    # Determinar servicio basado en el código postal.
    is_highlands = any(postcode.startswith(prefix) for prefix in HIGHLANDS_AND_ISLANDS_POSTCODES)
    service = STANDARD_SERVICE_NAME if is_highlands else NEXT_DAY_SERVICE_NAME

    # Determinar peso (lógica original)
    weight = 15
    if len(all_items_in_order) == 1:
        item = all_items_in_order[0]
        is_ct65_black = item.get('CARPET TYPE') == 'CT65' and item.get('CARPET COLOUR', '').upper() == 'BLACK'
        weight = 1 if is_ct65_black else 15

    return {
        'Name': first_item.get('FIRST NAME', ''),
        'SURNAME': first_item.get('LAST NAME', '') or '..',
        'Address_line_1': shuffled_add[0],
        'Address_line_2': shuffled_add[1],
        'Address_line_3': shuffled_add[2],
        'Postcode': postcode,
        'BarCode': first_item.get('FinalBarcode', ''), # Usamos el barcode del primer ítem como representativo del pedido.
        'COUNTRY': shuffled_add[3] if len(shuffled_add[3]) <= 3 else 'GB',
        'SERVICE': service,
        'WEIGHT': weight,
        'DESCRIPTION': 'Car Mats',
    }

def _format_tracking_row(item: Dict, order_id: str) -> Dict:
    """Formatea una fila para un archivo de tracking."""
    return {
        'Shipping Status': 'Shipped',
        'Order ID': str(order_id),
        'Item Number': str(item.get('Item Number', '')),
        'Item Title': item.get('Product Title', ''),
        'Custom Label': str(item.get('Raw SKU', '')).upper(),
        'Transaction ID': str(item.get('Transaction ID', '')),
        'Shipping Carrier Used': 'Hermes',
        'Tracking Number': '',
        'Barcode': str(order_id), # El "Barcode" en este archivo es el Order ID de eBay
        'Our_Barcode': item.get('FinalBarcode', ''), # Nuestro barcode interno único
    }

def _generate_filename(
    file_type: str, store_id: Optional[str], current_date: datetime, extension="xlsx", consolidated=False, config=None
) -> str:
    """Generador de nombres de archivo estandarizado."""
    date_str = current_date.strftime("%Y%m%d_%H%M")
    if consolidated:
        return f"{file_type}_CONSOLIDATED_{date_str}.{extension}"
    
    store_initials_map = config.get('STORE_INITIALS', {})
    store_initial = store_initials_map.get(store_id, store_id[:3].upper() if store_id else "UNK")
    return f"{file_type}_{store_initial}_{date_str}.{extension}"

def _group_items_by_order_id(items: List[Dict]) -> Dict[str, List[Dict]]:
    """Agrupa una lista de ítems en un diccionario por su Order ID."""
    groups = {}
    for item in items:
        order_id = item.get('ORDER ID')
        if order_id:
            groups.setdefault(order_id, []).append(item)
    return groups

def _group_items_by_store_id(items: List[Dict]) -> Dict[str, List[Dict]]:
    """Agrupa una lista de ítems en un diccionario por su Store ID."""
    groups = {}
    for item in items:
        store_id = item.get('Store ID')
        if store_id:
            groups.setdefault(store_id, []).append(item)
    return groups

def _shuffle_address(add1, add2, add3, add4) -> List[str]:
    """Mueve las partes de la dirección para rellenar huecos, asegurando 4 partes."""
    parts = [p for p in [add1, add2, add3, add4] if p and str(p).strip().lower() not in ('', 'n/a')]
    return (parts + [''] * 4)[:4]

def _save_excel_file(
    rows: List[Dict[str, Any]],
    output_dir: str,
    filename: str,
    sheet_title: str,
    config: Dict,
    has_info_header: bool = False,
) -> Optional[str]:
    """
    Función de ayuda centralizada y robusta para guardar una lista de diccionarios en un archivo Excel.
    Usa un archivo temporal para una escritura atómica y segura.
    """
    if not rows:
        logger.warning(f"No hay filas para escribir en el archivo {filename}. Se omitirá la creación.")
        return None

    file_path = os.path.join(output_dir, filename)
    temp_path = file_path + f".{os.getpid()}.tmp"

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_title[:30]  # Título de hoja con límite de caracteres

        # Escribir la cabecera opcional #INFO
        start_row = 1
        if has_info_header:
            ws.cell(row=1, column=1).value = INFO_HEADER_TAG
            start_row = 2
        
        # Escribir las cabeceras de columna
        headers = list(rows[0].keys())
        for col_idx, header_text in enumerate(headers, 1):
            ws.cell(row=start_row, column=col_idx).value = header_text

        # Columnas que deben ser tratadas como texto para evitar auto-formato de Excel
        text_format_columns = {'Barcode', 'Our_Barcode', 'ORDER ID', 'Item Number', 'Transaction ID', 'POSTCODE', 'TEL NO', 'SKU', 'Bar Code', 'Tracking No'}

        # Escribir las filas de datos
        for row_idx, data_row in enumerate(rows, start_row + 1):
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                # Sanear el valor antes de escribirlo
                value = sanitize_for_excel(data_row.get(header, ''))
                cell.value = value
                # Aplicar formato de texto si es una columna crítica
                if header in text_format_columns:
                    cell.number_format = '@'

        # Ajustar el ancho de las columnas
        for col_idx, header in enumerate(headers, 1):
            column_letter = get_column_letter(col_idx)
            # Calcular el ancho máximo basado en el contenido y la cabecera
            max_len = max([len(str(r.get(header, ''))) for r in rows] + [len(header)])
            adjusted_width = min(max(max_len + 2, 12), 50) # Ancho entre 12 y 50 caracteres
            ws.column_dimensions[column_letter].width = adjusted_width
        
        wb.save(temp_path)
        shutil.move(temp_path, file_path)

        logger.info(f"Archivo Excel generado exitosamente: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Fallo al guardar el archivo Excel {filename}: {e}", exc_info=True)
        # Limpiar el archivo temporal si existe
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise FileGenerationError(f"No se pudo generar el archivo {filename}", filename=filename) from e
    finally:
        if 'wb' in locals():
            wb.close()