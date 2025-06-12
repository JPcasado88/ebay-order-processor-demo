# ebay_processor/services/sku_matching.py

import logging
from typing import Dict, Any, Optional
import pandas as pd

from ..core.exceptions import SKUMatchingError
from ..utils.string_utils import normalize_ref_no
from ..utils.date_utils import check_year_match 
from .sku_id_extractor import extract_sku_identifier 

logger = logging.getLogger(__name__)


def find_best_match(
    sku: str,
    title: str,
    matlist_df: pd.DataFrame,
    car_details: Optional[Dict[str, str]]
) -> Optional[Dict[str, Any]]:
    
    if not isinstance(sku, str):
        sku = ''
    if not isinstance(title, str):
        title = ''

    try:
        filtered_df = _apply_bootmat_filter(title, matlist_df)

        if filtered_df.empty:
            logger.debug(f"No catalog candidates for title '{title[:50]}...' after bootmat filter.")
            return None

        forced_match = _match_by_forced_sku(sku, filtered_df)
        if forced_match is not None:
            logger.info(f"Success (ForcedMatch): SKU '{sku}' -> Template '{forced_match.get('Template')}'")
            return forced_match

        sku_identifier_match = _match_by_sku_identifier(sku, filtered_df)
        if sku_identifier_match is not None:
            logger.info(f"Success (Identifier): SKU '{sku}' -> Template '{sku_identifier_match.get('Template')}'")
            return sku_identifier_match
        
        if car_details:
            title_match = _match_by_title_details(car_details, filtered_df)
            if title_match is not None:
                logger.info(f"Success (Title Fallback): Title '{title[:50]}...' -> Template '{title_match.get('Template')}'")
                return title_match

        logger.warning(f"NO MATCH: SKU='{sku}', Title='{title[:50]}...'")
        return None

    except Exception as e:
        raise SKUMatchingError(f"Unexpected exception in matching engine: {e}", sku=sku, product_title=title) from e


def _apply_bootmat_filter(title: str, catalog_df: pd.DataFrame) -> pd.DataFrame:
    title_lower = title.lower()
    is_bootmat_title = "and bootmat" in title_lower or "with bootmat" in title_lower

    if is_bootmat_title:
        return catalog_df[catalog_df['Template'].str.strip().str.upper().str.startswith('MS-')]
    else:
        return catalog_df[
            ~catalog_df['Template'].str.strip().str.upper().str.startswith('BM-') &
            ~catalog_df['Template'].str.strip().str.upper().str.startswith('MS-')
        ]


def _match_by_forced_sku(sku: str, catalog_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    if '_normalized_forced_sku' not in catalog_df.columns:
        return None
        
    normalized_sku = str(sku).strip().lower()
    if not normalized_sku:
        return None

    match_rows = catalog_df[catalog_df['_normalized_forced_sku'] == normalized_sku]
    if not match_rows.empty:
        return match_rows.iloc[0].to_dict()

    return None


def _match_by_sku_identifier(sku: str, catalog_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    # Redundant local import has been removed.
    
    # Now uses the function imported at the top of the file.
    identifier = extract_sku_identifier(sku)
    if not identifier:
        return None

    normalized_id = normalize_ref_no(identifier)
    
    match_rows = catalog_df[catalog_df['Template_Normalized'] == normalized_id]
    if not match_rows.empty:
        return match_rows.iloc[0].to_dict()

    return None


def _match_by_title_details(car_details: Dict[str, str], catalog_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    make = car_details.get('make', '').lower()
    model_words_from_title = set(car_details.get('model', '').lower().split())

    if not make or not model_words_from_title:
        return None

    make_matches = catalog_df[catalog_df['COMPANY'].str.lower() == make]
    if make_matches.empty:
        return None

    best_match_row = None
    best_score = -1

    for _, row in make_matches.iterrows():
        model_words_from_csv = set(row.get('MODEL', '').lower().split())
        
        current_score = len(model_words_from_title.intersection(model_words_from_csv))
        
        if current_score > best_score:
            best_score = current_score
            best_match_row = row

    if best_match_row is not None and best_score > 0:
        product_year = car_details.get('year')
        catalog_year = best_match_row.get('YEAR')
        
        if product_year and catalog_year:
            if check_year_match(product_year, catalog_year):
                return best_match_row.to_dict()
            else:
                return None
        else:
            return best_match_row.to_dict()

    return None