# ebay_processor/utils/date_utils.py
"""
Date and Time Utilities Module.

Contains pure functions for parsing, formatting, validating and manipulating
date and time objects, as well as date-related text strings,
such as vehicle year ranges.
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
    Normalizes different year range formats to a standard format.

    Examples:
    - "2010+" -> "2010-present"
    - "2010 to present" -> "2010-present"
    - "2010 - 2015" -> "2010-2015"
    - "2010" -> "2010"

    Args:
        year_str: The year string to normalize.

    Returns:
        The normalized year string in lowercase.
    """
    if not year_str or not isinstance(year_str, str):
        return ""
    
    s = str(year_str).strip().lower()

    # Replace "2010+" or "2010 -" with "2010-present"
    s = re.sub(r'(\d{4})\s*(\+|-)\s*$', r'\1-present', s)
    
    # Replace "2010 to present" or "2010 onwards" with "2010-present"
    s = re.sub(r'(\d{4})\s*(?:to|onwards)\s*present', r'\1-present', s)

    # Standardize the dash
    s = re.sub(r'\s*[-–]\s*', '-', s) # Replace dashes with or without spaces with a single dash

    return s


def check_year_match(product_year_str: str, catalog_year_str: str) -> bool:
    """
    Checks if two year ranges (as strings) overlap.
    Handles formats like '2010-2015', '2018', '2020-present'.

    Args:
        product_year_str: The product year range (e.g., from title).
        catalog_year_str: The catalog year range (e.g., from CSV).

    Returns:
        True if the ranges overlap, False otherwise.
    """
    if not catalog_year_str or not product_year_str:
        return False

    def _parse_range(year_str: str) -> Optional[Tuple[int, int]]:
        """Internal function to convert a range string into a (start, end) tuple."""
        current_year = datetime.now().year
        # Normalize 'present', '+' and others to the current year.
        s = normalize_year_range(year_str).replace('present', str(current_year))
        
        # Extract all 4-digit numbers.
        years = re.findall(r'\d{4}', s)
        
        if not years:
            return None
        
        # Convert numbers to integers.
        year_nums = [int(y) for y in years]
        
        # Return the minimum and maximum as the range.
        return min(year_nums), max(year_nums)

    product_range = _parse_range(product_year_str)
    catalog_range = _parse_range(catalog_year_str)

    # If either range couldn't be parsed, no match.
    if not product_range or not catalog_range:
        return False

    p_start, p_end = product_range
    c_start, c_end = catalog_range

    # Overlap logic: the start of one range must be less than or equal
    # to the end of the other, AND the start of the other must be less than or equal
    # to the end of the first.
    return p_start <= c_end and c_start <= p_end