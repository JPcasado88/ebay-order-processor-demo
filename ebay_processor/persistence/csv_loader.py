# ebay_processor/persistence/csv_loader.py
"""
Reference Data (Catalog) Loading Module.

This module handles the loading and preparation of the master CSV file
(e.g., ktypemaster3.csv) that contains the product catalog.

The preparation includes:
- Selection and validation of required columns.
- Column renaming for internal consistency.
- Data cleaning and normalization to facilitate matching.
- Creation of derived columns to optimize searches.
"""

import logging
import re
from datetime import datetime
import pandas as pd

# Utilities for file loading and string normalization
from ..utils.file_utils import load_csv_to_dataframe
from ..utils.string_utils import normalize_ref_no
from ..core.exceptions import DataLoadingError
from ..core.constants import MasterDataColumns

logger = logging.getLogger(__name__)

def load_and_prepare_master_data(file_path: str) -> pd.DataFrame:
    """
    Loads and prepares the master catalog DataFrame from a CSV file.

    Args:
        file_path: The path to the ktypemaster3.csv file or similar.

    Returns:
        A clean pandas DataFrame ready to be used by the matching service.

    Raises:
        DataLoadingError: If the file cannot be loaded or has an invalid format.
    """
    logger.info(f"Starting loading and preparation of master data from: {file_path}")
    
    # Define the columns that are absolutely necessary for the app to function.
    required_cols = [
        MasterDataColumns.TEMPLATE, MasterDataColumns.COMPANY, MasterDataColumns.MODEL,
        MasterDataColumns.YEAR, MasterDataColumns.MATS, MasterDataColumns.NUM_CLIPS,
        MasterDataColumns.CLIP_TYPE
    ]
    
    # Load the CSV using our utility, which already validates the existence of columns.
    try:
        # We use `keep_default_na=False` to treat empty cells as "" instead of NaN,
        # which simplifies string handling.
        df = load_csv_to_dataframe(
            file_path, 
            required_columns=required_cols,
            keep_default_na=False,
            dtype=str  # Load everything as string initially to avoid type errors.
        )
    except DataLoadingError as e:
        logger.error(f"Could not load master data file: {e}", exc_info=True)
        raise

    # Optional columns that will be used if they exist.
    optional_cols = [MasterDataColumns.FORCED_MATCH_SKU]
    
    # Create a list of all columns to keep.
    cols_to_keep = required_cols + [col for col in optional_cols if col in df.columns]
    
    # Use a copy to avoid pandas SettingWithCopyWarning.
    df_cleaned = df[cols_to_keep].copy()
    
    # Rename columns for internal consistency in the application.
    df_cleaned.rename(columns={MasterDataColumns.NUM_CLIPS: MasterDataColumns.INTERNAL_CLIP_COUNT}, inplace=True)
    
    # --- Data Cleaning and Normalization ---

    # Normalize the YEAR column: replace "to present" with the current year.
    current_year = str(datetime.now().year)
    df_cleaned[MasterDataColumns.YEAR] = df_cleaned[MasterDataColumns.YEAR].str.replace(
        r'to\s+present', f'-{current_year}', flags=re.IGNORECASE, regex=True
    )
    
    # Normalize key text columns: to lowercase and remove extra spaces.
    text_cols_to_normalize = [
        MasterDataColumns.COMPANY, MasterDataColumns.MODEL, MasterDataColumns.YEAR,
        MasterDataColumns.CLIP_TYPE, MasterDataColumns.TEMPLATE
    ]
    for col in text_cols_to_normalize:
        df_cleaned[col] = df_cleaned[col].str.lower().str.strip()

    # --- Creation of Derived Columns for Matching ---

    # Create a 'Template_Normalized' column for fast and exact searches.
    # E.g.: "MS-123 AB" -> "MS123AB"
    df_cleaned[MasterDataColumns.NORMALIZED_TEMPLATE] = df_cleaned[MasterDataColumns.TEMPLATE].apply(normalize_ref_no)
    
    # Create a normalized column for 'ForcedMatchSKU' if it exists.
    if MasterDataColumns.FORCED_MATCH_SKU in df_cleaned.columns:
        df_cleaned['_normalized_forced_sku'] = df_cleaned[MasterDataColumns.FORCED_MATCH_SKU].str.strip().str.lower()

    logger.info(f"Master DataFrame prepared. Total rows: {len(df_cleaned)}. Columns: {list(df_cleaned.columns)}")
    
    return df_cleaned