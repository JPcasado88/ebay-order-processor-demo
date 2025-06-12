# ebay_processor/services/car_details_extractor.py
"""
Vehicle Details Extraction Service.
...
"""

import logging
import re
from typing import Dict, Optional

# Import utilities from the correct modules.
from ..utils.string_utils import normalize_make, normalize_model
from ..utils.date_utils import normalize_year_range # <<< Imported from its new home.

logger = logging.getLogger(__name__)

class CarDetailsExtractor:
    """
    Encapsulates the logic for extracting make, model and year from a product title.
    """

    # Common words in titles that don't provide vehicle information
    # and may interfere with extraction.
    NOISE_WORDS = [
        'tailored', 'carpet', 'car mats', 'floor mats', 'set', '4pcs', '5pcs', 'pc',
        'heavy duty', 'rubber', 'solid trim', 'uk made', 'custom', 'fully',
        'black', 'grey', 'blue', 'red', 'beige', 'with', 'trim', 'edge', 'for', 'fits'
    ]
    
    # Main and most reliable regex pattern. Looks for the structure:
    # (Make) (Model) (Year)
    # - Make is one or more words.
    # - Model is anything until the year is found.
    # - Year has various formats: 2010-2015, 2020+, 2024, etc.
    VEHICLE_PATTERN = re.compile(
        # Group 1: Make (non-greedy)
        r'([A-Za-z\s\-]+?)\s+'
        # Group 2: Model (any character, non-greedy)
        r'(.*?)\s+'
        # Group 3: Year (multiple formats)
        r'(\d{4}\s*[-–to]+\s*\d{4}|\d{4}\s*[-–to]+\s*present|\d{4}\s*\+?|\d{4})',
        re.IGNORECASE
    )

    def _clean_title(self, title: str) -> str:
        """
        Pre-processes the title to remove noise and facilitate extraction.
        
        Args:
            title: The original product title.

        Returns:
            The cleaned title.
        """
        # Remove content within brackets, e.g.: [Black with Red Trim]
        clean_title = re.sub(r'\[.*?\]', ' ', title)
        
        # Remove the "noise" words defined in the class.
        # Build a regex to search for any of these complete words (\b).
        noise_pattern = r'\b(' + '|'.join(self.NOISE_WORDS) + r')\b'
        clean_title = re.sub(noise_pattern, ' ', clean_title, flags=re.IGNORECASE)
        
        # Normalize multiple spaces to single spaces.
        return ' '.join(clean_title.split())

    def extract(self, title: str) -> Optional[Dict[str, str]]:
        """
        Main method for extracting vehicle details from a title.

        Args:
            title: The eBay product title.

        Returns:
            A dictionary with 'make', 'model' and 'year' if a match is found,
            or None otherwise.
        """
        if not isinstance(title, str):
            return None
        
        clean_title = self._clean_title(title)
        
        match = self.VEHICLE_PATTERN.search(clean_title)
        
        if not match:
            logger.debug(f"Could not extract details from title: '{title}' (clean: '{clean_title}')")
            return None
            
        make_raw, model_raw, year_raw = match.groups()
        
        # Use our utility functions to normalize the results.
        make = normalize_make(make_raw)
        model = normalize_model(model_raw)
        year = normalize_year_range(year_raw)
        
        # Final verification: make sure make and model are not empty.
        if not make or not model:
            logger.warning(f"Partial extraction for '{title}'. Make or Model empty after normalizing.")
            return None

        logger.info(f"Title '{title[:50]}...' -> Extracted: Make='{make}', Model='{model}', Year='{year}'")
        return {
            'make': make,
            'model': model,
            'year': year
        }