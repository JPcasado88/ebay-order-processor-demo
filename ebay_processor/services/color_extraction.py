# ebay_processor/services/color_extraction.py
"""
Product Color Extraction Service.

This service specializes in a complex task: determining the carpet color
and trim color from an eBay product title.
The logic is designed to handle a wide variety of title formats,
prioritizing explicit contexts over assumptions.
"""

import logging
import re
from typing import Tuple

# Import constants to maintain consistency
from ..core.constants import ALLOWED_COLORS, Carpet, Embroidery

logger = logging.getLogger(__name__)

def extract_carpet_and_trim_colors(title: str) -> Tuple[str, str]:
    """
    Analyzes a product title to extract carpet and trim colors.

    The process follows a priority order:
    1.  Determines if it's a rubber carpet ('Rubber'). If so, carpet color is 'Rubber'.
    2.  Looks for explicit mentions like "Red Trim" or "Black Carpet". These have maximum priority.
    3.  Analyzes complex patterns within brackets, like "[Color with Color Trim]".
    4.  As a last resort, searches for colors in the title and assigns them based on position.
    5.  Applies intelligent defaults if either color is not found.

    Args:
        title: The eBay product title.

    Returns:
        A tuple with (carpet_color, trim_color). Both are capitalized strings.
        E.g.: ('Black', 'Red'), ('Grey', 'Grey'), ('Rubber', 'Black').
    """
    # -------------------
    # 1. Initialization and Cleaning
    # -------------------
    if not isinstance(title, str):
        logger.warning(f"Received invalid title (type: {type(title)}). Using defaults.")
        return 'Black', 'Black'

    title_lower = title.lower().strip()
    
    # Default values that will be overwritten if something is found
    carpet_color = 'Black'
    trim_color = 'Black'

    # -------------------
    # 2. Rubber Detection
    # -------------------
    # This is the most important rule and should go first.
    # If it's rubber, carpet color is always 'Rubber'.
    is_rubber = any(rubber_keyword in title_lower for rubber_keyword in ['rubber', 'rubstd', 'rubhd', '5mm'])
    if is_rubber:
        carpet_color = 'Rubber'
        # Don't exit yet, because a rubber carpet can have a specific trim color.
        logger.debug(f"Title '{title[:30]}...': Detected as Rubber. Carpet='Rubber'.")

    # -------------------
    # 3. Explicit Context Search (Maximum Priority)
    # -------------------
    # Patterns like "Red Trim" or "Blue Carpet" are the most reliable.
    # We use finditer to search for all occurrences and keep the last one,
    # which is usually correct in complex titles.
    
    # Search for "Color Trim" or "Color Edge"
    explicit_trim_match = re.search(r'\b(' + '|'.join(ALLOWED_COLORS) + r')\s+(trim|edge)\b', title_lower)
    if explicit_trim_match:
        trim_color = explicit_trim_match.group(1).capitalize()
        logger.debug(f"Title '{title[:30]}...': Found explicit Trim: '{trim_color}'.")
        
    # Search for "Color Carpet" (only if not rubber)
    if not is_rubber:
        explicit_carpet_match = re.search(r'\b(' + '|'.join(ALLOWED_COLORS) + r')\s+carpet\b', title_lower)
        if explicit_carpet_match:
            carpet_color = explicit_carpet_match.group(1).capitalize()
            logger.debug(f"Title '{title[:30]}...': Found explicit Carpet: '{carpet_color}'.")

    # -------------------
    # 4. Complex Pattern Analysis (within brackets)
    # -------------------
    # Many titles use brackets to specify variations.
    # E.g.: "[Black with Red Trim,Does Not Apply]"
    bracket_content_match = re.search(r'\[(.*?)\]', title_lower)
    if bracket_content_match:
        content = bracket_content_match.group(1)
        
        # Pattern: "Color1 with Color2 Trim"
        with_trim_pattern = re.search(r'\b(' + '|'.join(ALLOWED_COLORS) + r')\s+with\s+(' + '|'.join(ALLOWED_COLORS) + r')\s+trim\b', content)
        if with_trim_pattern:
            # If we find this pattern, it's very reliable and overrides the previous.
            if not is_rubber:
                carpet_color = with_trim_pattern.group(1).capitalize()
            trim_color = with_trim_pattern.group(2).capitalize()
            logger.debug(f"Title '{title[:30]}...': 'with trim' pattern found. Carpet='{carpet_color}', Trim='{trim_color}'.")

    # -------------------
    # 5. Fallback: Search for Colors without Context
    # -------------------
    # If after all of the above we still have default values,
    # search for any color mentioned and assign it.
    
    # Create a list of all colors found in the title.
    found_colors = [color for color in ALLOWED_COLORS if re.search(r'\b' + color + r'\b', title_lower)]
    
    if found_colors:
        # If carpet is still 'Black' by default (and not rubber),
        # assign the first color found in the title.
        if carpet_color == 'Black' and not is_rubber:
            # Exclude the color that might already be assigned to trim to avoid duplicates.
            available_colors = [c for c in found_colors if c.capitalize() != trim_color]
            if available_colors:
                carpet_color = available_colors[0].capitalize()
                logger.debug(f"Title '{title[:30]}...': Fallback assigned Carpet='{carpet_color}'.")

    # -------------------
    # 6. Final Intelligent Defaults Logic
    # -------------------
    # If trim is still the default 'Black' but carpet has a color,
    # it's very likely that trim is the same color as carpet.
    # E.g.: Title "Red Car Mats" -> Carpet='Red', Trim should be 'Red', not 'Black'.
    if trim_color == 'Black' and carpet_color not in ['Black', 'Rubber']:
        trim_color = carpet_color
        logger.debug(f"Title '{title[:30]}...': Intelligent defaulting, Trim same as Carpet: '{trim_color}'.")
        
    logger.info(f"Title: '{title[:50]}...' -> Extracted: Carpet='{carpet_color}', Trim='{trim_color}'.")
    return carpet_color, trim_color


def determine_carpet_type(title: str) -> str:
    """
    Determines carpet type (CT65, Velour, Rubber) from the title.

    Args:
        title: The eBay product title.

    Returns:
        A string representing the carpet type (using `Carpet` constants).
    """
    if not isinstance(title, str):
        return Carpet.STANDARD # Default value

    title_lower = title.lower()
    
    if 'velour' in title_lower:
        return Carpet.VELOUR
    if '5mm' in title_lower or 'heavy duty rubber' in title_lower:
        return Carpet.RUBBER_HD
    if 'rubber' in title_lower:
        return Carpet.RUBBER_STD
        
    return Carpet.STANDARD


def determine_embroidery_type(title: str) -> str:
    """
    Determines embroidery type from the title.

    Args:
        title: The eBay product title.

    Returns:
        "Double Stitch" or an empty string (using `Embroidery` constants).
    """
    if not isinstance(title, str):
        return Embroidery.NONE # Default value

    # Keywords that indicate "Double Stitch"
    keywords = ["GREYDS", "BLACKDS", "REDS", "BLUEDS", "UPGRADED", "DOUBLE STITCH"]
    
    title_upper = title.upper()
    if any(keyword in title_upper for keyword in keywords):
        return Embroidery.DOUBLE_STITCH
        
    return Embroidery.NONE