# ebay_processor/services/sku_id_extractor.py
"""
SKU Identifier Extraction Service.

This module contains specialized logic for extracting the main template 
identifier from a product SKU string, which can have multiple formats 
and variations.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# Color keyword list, moved to module level for reuse.
COLOR_KEYWORDS: List[str] = [
    'BLACK', 'BLUE', 'GREY', 'RED', 'GREEN', 'YELLOW', 
    'SILVER', 'WHITE', 'TRIM', 'SOLID', 'BEIGE', 'TAN', 'ORANGE',
    'PURPLE', 'BROWN', 'PINK'
]

def extract_sku_identifier(sku):
    """
    Extracts the primary identifier from a product SKU string based on a prioritized
    list of known patterns and exceptions. Includes specific handling for various
    code formats and a mapping rule for specific numeric codes (e.g., 8435 -> L2).
    Uses a multi-stage fallback mechanism for unidentified or embedded codes.

    Args:
        sku (str): The SKU string to process.

    Returns:
        str: The extracted (and potentially mapped) identifier string, uppercased,
             or the original SKU (uppercased) if no specific pattern is matched.
             Returns an empty string if the input is not a valid string.
    """
    if not isinstance(sku, str):
        logging.error("Input SKU is not a string.")
        return ''

    sku = sku.strip()
    original_sku_for_logging = sku # Keep original for final warning if needed

    logging.debug(f"Starting extraction for SKU: '{sku}'")

    # == EXCEPTION CASES ==
    if sku.upper() == "R-VAW0212":
        logging.debug("Exact match override (R-VAW0212) detected.")
        return "R-VAW0212"

    # == PREFIX REMOVAL ==
    if sku.upper().startswith("CT65 "):
        sku = sku[5:].strip()
        logging.debug(f"Removed CT65 prefix, SKU is now: '{sku}'")

    # == PRIORITIZED PATTERN MATCHING (using re.match for start-of-string) ==

    # CASE 1: V-codes (e.g., V94, V123)
    v_pattern = re.match(r'^(V\d+)', sku, re.IGNORECASE)
    if v_pattern:
        identifier = v_pattern.group(1).upper()
        logging.debug(f"V-code pattern (CASE 1) detected: extracted '{identifier}'")
        return identifier

    # CASE 2: [Letter]-VAW pattern with multiple parts (e.g., G-VAW 1 1 X74 -> X74)
    vaw_pattern = re.match(r'^[A-Za-z]-VAW\d+\s+\d+\s+([A-Za-z]\d+)', sku, re.IGNORECASE)
    if vaw_pattern:
        identifier = vaw_pattern.group(1).upper()
        logging.debug(f"[Letter]-VAW pattern (CASE 2) detected: extracted '{identifier}'")
        return identifier

    # CASE 3: ABNH pattern (e.g., C1BNH)
    abnh_pattern = re.match(r'^([A-Za-z]\d+BNH)', sku, re.IGNORECASE)
    if abnh_pattern:
        identifier = abnh_pattern.group(1).upper()
        logging.debug(f"ABNH pattern (CASE 3) detected: extracted '{identifier}'")
        return identifier

    # CASE 4: X-HOLES/NOHOLES pattern (e.g., Q80-NOHOLES, M6-HOLES)
    holes_pattern = re.match(r'^([A-Za-z0-9]+[-][A-Za-z0-9]*(?:HOLES|NOHOLES))', sku, re.IGNORECASE)
    if holes_pattern:
        identifier = holes_pattern.group(1).upper()
        logging.debug(f"X-HOLES pattern (CASE 4) detected: extracted '{identifier}'")
        return identifier

    # CASE 5: HOLES/NOHOLES pattern (Search - Less precise)
    if "HOLES" in sku.upper() and not holes_pattern:
        holes_pattern_search = re.search(r'([A-Za-z0-9]+(?:HOLES|NOHOLES))', sku, re.IGNORECASE)
        if holes_pattern_search:
            identifier = holes_pattern_search.group(1).upper()
            logging.debug(f"HOLES pattern search (CASE 5) detected: extracted '{identifier}'")
            return identifier

    # CASE 6: VELOUR pattern (e.g., VELOUR 1 1 M4 -> M4)
    if sku.upper().startswith("VELOUR"):
        parts = sku.split()
        if len(parts) >= 3:
            last_part_velour = parts[-1].strip().upper()
            if re.match(r'^[A-Za-z]\d+$', last_part_velour):
                 identifier = last_part_velour
                 logging.debug(f"VELOUR pattern (CASE 6) detected: extracted '{identifier}'")
                 return identifier
            else:
                 logging.debug(f"VELOUR pattern (CASE 6) matched, but last part '{last_part_velour}' not Letter+Digit format. Continuing.")

    # CASE 7: ZZ pattern (e.g., ZZ231, ZZ231D)
    zz_pattern = re.match(r'^(ZZ\d+[A-Za-z]?)', sku, re.IGNORECASE)
    if zz_pattern:
        identifier = zz_pattern.group(1).upper()
        logging.debug(f"ZZ pattern (CASE 7) detected: extracted '{identifier}'")
        return identifier

    # CASE 8: G-VAW pattern (e.g., G-VAW 1 1 X74 -> X74)
    if sku.upper().startswith("G-VAW"):
        parts = sku.split()
        if len(parts) >= 3:
            last_part_gvaw = parts[-1].strip().upper()
            if re.match(r'^[A-Za-z]\d+$', last_part_gvaw):
                identifier = last_part_gvaw
                logging.debug(f"G-VAW pattern (CASE 8) detected: extracted '{identifier}'")
                return identifier
            else:
                logging.debug(f"G-VAW pattern (CASE 8) matched, but last part '{last_part_gvaw}' not standard format. Continuing.")

    # CASE 9: X-number pattern (e.g., X180-1)
    x_pattern = re.match(r'^(X\d+-\d+)', sku, re.IGNORECASE)
    if x_pattern:
        identifier = x_pattern.group(1).upper()
        logging.debug(f"X-number pattern (CASE 9) detected: extracted '{identifier}'")
        return identifier

    # CASE 10: MS- pattern (e.g., MS-C2, MS-Q80, MS-C2-E)
    ms_pattern = re.match(r'^(MS-[A-Za-z0-9]+(?:-[A-Za-z0-9])?)', sku, re.IGNORECASE)
    if ms_pattern:
        identifier = ms_pattern.group(1).upper()
        logging.debug(f"MS- pattern (CASE 10) detected: extracted '{identifier}'")
        return identifier

    # CASE 11: Q-codes (e.g., Q80, Q43-CC)
    q_pattern = re.match(r'^(Q\d+(?:-[A-Za-z0-9]+)?)', sku, re.IGNORECASE)
    if q_pattern:
        identifier = q_pattern.group(1).upper()
        logging.debug(f"Q-code pattern (CASE 11) detected: extracted '{identifier}'")
        return identifier

    # CASE 12: Short Suffix pattern (e.g., C2-E, A5-8)
    suffix_pattern = re.match(r'^([A-Za-z0-9]+-[A-Za-z0-9])(?![A-Za-z0-9])', sku, re.IGNORECASE)
    if suffix_pattern:
        identifier = suffix_pattern.group(1).upper()
        logging.debug(f"Short Suffix pattern (CASE 12) detected: extracted '{identifier}'")
        return identifier

    # CASE 13: Simple Letter+Number codes at the start (e.g., C2, A5, M6 CVT)
    single_letter_pattern = re.match(r'^([A-Za-z]\d+[A-Za-z]*)(?:\s+CVT)?', sku, re.IGNORECASE)
    if single_letter_pattern:
        potential_identifier_base = single_letter_pattern.group(1).upper()
        check_suffix = re.match(rf'^({re.escape(potential_identifier_base)}-[A-Za-z0-9])(?![A-Za-z0-9])', sku, re.IGNORECASE)
        if check_suffix:
             identifier = check_suffix.group(1).upper()
             logging.debug(f"Single letter+Num pattern (CASE 13) matched with secondary suffix check: '{identifier}'")
             return identifier
        else:
            identifier = potential_identifier_base
            logging.debug(f"Single letter+Num pattern (CASE 13) detected: extracted '{identifier}'")
            return identifier

    # CASE 14: "Code - Color/Trim" pattern (e.g., Q80 - Black -> Q80)
    if ' - ' in sku:
        parts = sku.split(' - ', 1)
        potential_base = parts[0].strip()
        suffix_part = parts[1].upper()
        color_keywords = ['BLACK', 'BLUE', 'GREY', 'RED', 'GREEN', 'YELLOW', 'SILVER', 'WHITE', 'TRIM', 'SOLID']
        if any(color in suffix_part for color in color_keywords):
            logging.debug(f"Color trim pattern (CASE 14) detected. Re-evaluating base part: '{potential_base}'")
            # Re-evaluation logic (same as before)
            ms_match_rerun = re.match(r'^(MS-[A-Za-z0-9]+(?:-[A-Za-z0-9])?)', potential_base, re.IGNORECASE)
            q_match_rerun = re.match(r'^(Q\d+(?:-[A-Za-z0-9]+)?)', potential_base, re.IGNORECASE)
            suffix_match_rerun = re.match(r'^([A-Za-z0-9]+-[A-Za-z0-9])(?![A-Za-z0-9])', potential_base, re.IGNORECASE)
            single_letter_rerun = re.match(r'^([A-Za-z]\d+[A-Za-z]*)(?:\s+CVT)?', potential_base, re.IGNORECASE)
            if ms_match_rerun: identifier = ms_match_rerun.group(1).upper(); logging.debug(f"Re-evaluation matched MS: '{identifier}'"); return identifier
            if q_match_rerun: identifier = q_match_rerun.group(1).upper(); logging.debug(f"Re-evaluation matched Q: '{identifier}'"); return identifier
            if suffix_match_rerun: identifier = suffix_match_rerun.group(1).upper(); logging.debug(f"Re-evaluation matched Suffix: '{identifier}'"); return identifier
            if single_letter_rerun:
                 base_rerun = single_letter_rerun.group(1).upper()
                 check_suffix_rerun = re.match(rf'^({re.escape(base_rerun)}-[A-Za-z0-9])(?![A-Za-z0-9])', potential_base, re.IGNORECASE)
                 if check_suffix_rerun: identifier = check_suffix_rerun.group(1).upper(); logging.debug(f"Re-evaluation matched Single+SuffixChk: '{identifier}'"); return identifier
                 else: identifier = base_rerun; logging.debug(f"Re-evaluation matched Single: '{identifier}'"); return identifier
            identifier = potential_base.upper()
            if identifier.endswith(" CVT"): identifier = identifier[:-4].strip()
            logging.debug(f"Color trim pattern confirmed (no refinement needed): extracted '{identifier}'")
            return identifier

    # CASE 15: VAW- prefix pattern (e.g., VAW-W0692 -> W0692)
    vaw_prefix_pattern = re.match(r'^VAW-?([A-Za-z]\d+)', sku, re.IGNORECASE)
    if vaw_prefix_pattern:
        identifier = vaw_prefix_pattern.group(1).upper()
        logging.debug(f"VAW Prefix pattern (VAW+Letter+Digits) (CASE 15) detected: extracted '{identifier}'")
        return identifier

    # CASE 16: VAW<digits> ... <LastPart> pattern (e.g., VAW0324 004 F2 -> F2)
    vaw_num_pattern = re.match(r'^VAW\d+\b', sku, re.IGNORECASE)
    if vaw_num_pattern and ' ' in sku:
        parts = sku.split()
        if len(parts) > 1:
            last_part_vawnum = parts[-1].strip().upper()
            if re.match(r'^[A-Za-z]\d+$', last_part_vawnum):
                identifier = last_part_vawnum
                logging.debug(f"VAW+Digits+LastPart (Letter+Digit) pattern (CASE 16) detected: extracted '{identifier}'")
                return identifier
            else:
                logging.debug(f"VAW+Digits pattern (CASE 16) matched, but last part '{last_part_vawnum}' not Letter+Digit format. Continuing.")
        else:
             logging.debug(f"VAW+Digits pattern (CASE 16) matched, but only one part? Skipping.")

    # CASE 17: Digit-Start pattern (e.g., 8435-grey -> 8435, 12345 -> 12345)
    # Includes specific mapping for 8435 -> L2.
    digit_start_pattern = re.match(r'^(\d+)\b', sku)
    if digit_start_pattern:
        identifier = digit_start_pattern.group(1)
        logging.debug(f"Digit-Start pattern (CASE 17) detected: extracted '{identifier}'")
        # *** ADDED MAPPING RULE HERE ***
        if identifier == "8435":
            mapped_identifier = "L2"
            logging.debug(f"Applying mapping rule: '{identifier}' -> '{mapped_identifier}'")
            identifier = mapped_identifier
        # ******************************
        return identifier

    # == FALLBACK MECHANISMS (using re.findall for searching anywhere) ==

    # CASE 18: Fallback - Search for simple Letter+Number codes (e.g., C2, B2)
    simple_search = re.findall(r'\b([A-Za-z]\d+)\b', sku, re.IGNORECASE)
    if not simple_search:
        simple_search = re.findall(r'([A-Za-z]\d+)', sku, re.IGNORECASE)
    if simple_search:
        identifier = simple_search[-1].upper()
        logging.debug(f"Fallback Search pattern (CASE 18 - Simple L+N) detected, using last match: '{identifier}' from {simple_search}")
        return identifier

    # CASE 19: Last Resort Fallback - Broad search for any Letter+Num or Num+Letter pattern.
    fallback_matches = re.findall(r'([A-Za-z]+\d+|\d+[A-Za-z]+)', sku, re.IGNORECASE)
    if fallback_matches:
        identifier = fallback_matches[-1].upper()
        logging.debug(f"Fallback Findall pattern (CASE 19 - Broad) detected, using last match: '{identifier}' from {fallback_matches}")
        return identifier

    # == FINAL: NO MATCH ==
    final_sku = original_sku_for_logging.upper()
    logging.warning(f"No specific pattern matched SKU '{original_sku_for_logging}'. Returning uppercased original: '{final_sku}'")
    return final_sku