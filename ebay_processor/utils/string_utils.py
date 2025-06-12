# ebay_processor/utils/string_utils.py
"""
String Utilities Module.

Contains helper functions for string manipulation, cleaning, normalization
and comparison.
"""
import re
from difflib import SequenceMatcher
from typing import Optional

def calculate_similarity(a: Optional[str], b: Optional[str]) -> float:
    """
    Calculates the similarity ratio between two strings using SequenceMatcher.
    The comparison is case-insensitive.

    Args:
        a: First text string.
        b: Second text string.

    Returns:
        A float between 0.0 and 1.0 representing the similarity.
    """
    # Convert to string and lowercase for robust comparison.
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def normalize_ref_no(ref_no: Optional[str]) -> str:
    """
    Normalizes a reference number (REF NO) by removing spaces and dashes,
    and converting to uppercase for consistent comparison.

    Args:
        ref_no: The reference number to normalize.

    Returns:
        The normalized reference number.
    """
    if not ref_no:
        return ""
    return re.sub(r'[\s\-]', '', str(ref_no)).upper()

def normalize_make(make: Optional[str]) -> str:
    """
    Normalizes car manufacturer names to a standard format.

    Args:
        make: The manufacturer name.

    Returns:
        The normalized manufacturer name in lowercase.
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
        'range rover': 'land rover', # Often used as a brand
        'alfa': 'alfa romeo',
        'alfa-romeo': 'alfa romeo',
        'chevy': 'chevrolet',
        'citreon': 'citroen',
    }
    
    return make_map.get(make_lower, make_lower)

def normalize_model(model: Optional[str]) -> str:
    """
    Cleans and normalizes car model names.

    Args:
        model: The model name.

    Returns:
        The cleaned and normalized model name.
    """
    if not model:
        return ""
    
    s = str(model).lower().strip()
    # Remove common words that don't add value
    s = re.sub(r'\b(car|auto|automobile|vehicle|floor|mats)\b', '', s, flags=re.IGNORECASE)
    # Remove special characters, but keep letters, numbers, spaces and dashes
    s = re.sub(r'[^\w\s-]', '', s)
    # Replace multiple spaces with a single one
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s

def sanitize_for_excel(text: Optional[str]) -> str:
    """
    Removes illegal control characters that can corrupt an Excel file.

    Args:
        text: The text to sanitize.

    Returns:
        The sanitized text.
    """
    if text is None:
        return ""
    # Regex to find control characters except tab, newline, etc.
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', str(text))