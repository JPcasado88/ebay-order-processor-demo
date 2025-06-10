# ebay_processor/utils/string_utils.py
"""
Módulo de Utilidades de Strings.

Contiene funciones de ayuda para la manipulación, limpieza, normalización
y comparación de cadenas de texto.
"""
import re
from difflib import SequenceMatcher
from typing import Optional

def calculate_similarity(a: Optional[str], b: Optional[str]) -> float:
    """
    Calcula la ratio de similitud entre dos strings usando SequenceMatcher.
    La comparación es insensible a mayúsculas/minúsculas.

    Args:
        a: Primera cadena de texto.
        b: Segunda cadena de texto.

    Returns:
        Un float entre 0.0 y 1.0 representando la similitud.
    """
    # Se convierten a string y a minúsculas para una comparación robusta.
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def normalize_ref_no(ref_no: Optional[str]) -> str:
    """
    Normaliza un número de referencia (REF NO) eliminando espacios y guiones,
    y convirtiéndolo a mayúsculas para una comparación consistente.

    Args:
        ref_no: El número de referencia a normalizar.

    Returns:
        El número de referencia normalizado.
    """
    if not ref_no:
        return ""
    return re.sub(r'[\s\-]', '', str(ref_no)).upper()

def normalize_make(make: Optional[str]) -> str:
    """
    Normaliza nombres de fabricantes de coches a un formato estándar.

    Args:
        make: El nombre del fabricante.

    Returns:
        El nombre del fabricante normalizado y en minúsculas.
    """
    if not make:
        return ""
    
    make_lower = str(make).lower().strip()
    
    make_map = {
        'vw': 'volkswagen',
        'volkswagon': 'volkswagen',
        'merc': 'mercedes',
        'mercedes-benz': 'mercedes',
        'mercedes benz': 'mercedes',
        'bmw': 'bmw',
        'landrover': 'land rover',
        'range rover': 'land rover', # A menudo se usa como marca
        'alfa': 'alfa romeo',
        'alfa-romeo': 'alfa romeo',
        'chevy': 'chevrolet',
        'citreon': 'citroen',
    }
    
    return make_map.get(make_lower, make_lower)

def normalize_model(model: Optional[str]) -> str:
    """
    Limpia y normaliza nombres de modelos de coches.

    Args:
        model: El nombre del modelo.

    Returns:
        El nombre del modelo limpio y normalizado.
    """
    if not model:
        return ""
    
    s = str(model).lower().strip()
    # Elimina palabras comunes que no aportan valor
    s = re.sub(r'\b(car|auto|automobile|vehicle|floor|mats)\b', '', s, flags=re.IGNORECASE)
    # Elimina caracteres especiales, pero conserva letras, números, espacios y guiones
    s = re.sub(r'[^\w\s-]', '', s)
    # Reemplaza múltiples espacios por uno solo
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s

def sanitize_for_excel(text: Optional[str]) -> str:
    """
    Elimina caracteres de control ilegales que pueden corromper un archivo Excel.

    Args:
        text: El texto a sanear.

    Returns:
        El texto saneado.
    """
    if text is None:
        return ""
    # Regex para encontrar caracteres de control excepto tab, newline, etc.
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', str(text))