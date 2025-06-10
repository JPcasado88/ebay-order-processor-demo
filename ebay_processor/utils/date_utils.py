# ebay_processor/utils/date_utils.py
"""
Módulo de Utilidades de Fecha y Hora.

Contiene funciones puras para parsear, formatear, validar y manipular
objetos de fecha y hora, así como cadenas de texto relacionadas con fechas,
como los rangos de años de los vehículos.
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def parse_ebay_datetime(ebay_time):
    """
    Parse eBay datetime string or object with correct timezone handling.
    
    Args:
        ebay_time: Either a string or datetime object from eBay
        
    Returns:
        datetime: Datetime object with correct timezone
    """
    try:
        # Check if already a datetime object
        if isinstance(ebay_time, datetime):
            dt = ebay_time
        else:
            # Parse the datetime string to a naive datetime object
            dt = datetime.strptime(ebay_time, '%Y-%m-%dT%H:%M:%S.%fZ')
        
        # If the datetime is naive (no timezone info), set it to UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt
    except Exception as e:
        logging.error(f"Error parsing eBay datetime: {str(e)} - Input type: {type(ebay_time)}")
        # Log a bit of the input for debugging if it's a string
        if isinstance(ebay_time, str):
            logging.error(f"Input sample: {ebay_time[:30]}...")
        return None

def normalize_year_range(year_str: str) -> str:
    """
    Normaliza diferentes formatos de rangos de años a un formato estándar.

    Ejemplos:
    - "2010+" -> "2010-present"
    - "2010 to present" -> "2010-present"
    - "2010 - 2015" -> "2010-2015"
    - "2010" -> "2010"

    Args:
        year_str: La cadena de texto del año a normalizar.

    Returns:
        La cadena de texto del año normalizada y en minúsculas.
    """
    if not year_str or not isinstance(year_str, str):
        return ""
    
    s = str(year_str).strip().lower()

    # Reemplazar "2010+" o "2010 -" por "2010-present"
    s = re.sub(r'(\d{4})\s*(\+|-)\s*$', r'\1-present', s)
    
    # Reemplazar "2010 to present" o "2010 onwards" por "2010-present"
    s = re.sub(r'(\d{4})\s*(?:to|onwards)\s*present', r'\1-present', s)

    # Estandarizar el guion
    s = re.sub(r'\s*[-–]\s*', '-', s) # Reemplaza guiones con o sin espacios por un solo guion

    return s


def check_year_match(product_year_str: str, catalog_year_str: str) -> bool:
    """
    Comprueba si dos rangos de años (como strings) se solapan.
    Maneja formatos como '2010-2015', '2018', '2020-present'.

    Args:
        product_year_str: El rango de años del producto (e.g., del título).
        catalog_year_str: El rango de años del catálogo (e.g., del CSV).

    Returns:
        True si los rangos se solapan, False en caso contrario.
    """
    if not catalog_year_str or not product_year_str:
        return False

    def _parse_range(year_str: str) -> Optional[Tuple[int, int]]:
        """Función interna para convertir un string de rango en una tupla (inicio, fin)."""
        current_year = datetime.now().year
        # Normaliza 'present', '+' y otros a el año actual.
        s = normalize_year_range(year_str).replace('present', str(current_year))
        
        # Extrae todos los números de 4 dígitos.
        years = re.findall(r'\d{4}', s)
        
        if not years:
            return None
        
        # Convierte los números a enteros.
        year_nums = [int(y) for y in years]
        
        # Devuelve el mínimo y el máximo como el rango.
        return min(year_nums), max(year_nums)

    product_range = _parse_range(product_year_str)
    catalog_range = _parse_range(catalog_year_str)

    # Si alguno de los rangos no se pudo parsear, no hay coincidencia.
    if not product_range or not catalog_range:
        return False

    p_start, p_end = product_range
    c_start, c_end = catalog_range

    # La lógica de solapamiento: el inicio de un rango debe ser menor o igual
    # que el final del otro, Y el inicio del otro debe ser menor o igual que
    # el final del primero.
    return p_start <= c_end and c_start <= p_end