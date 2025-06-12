# ebay_processor/utils/file_utils.py
"""
File and File System Utilities Module.

Provides helper functions for interacting with the file system,
such as loading data from files, cleaning directories and handling paths
safely and with proper logging.
"""
import os
import shutil
import glob
import logging
import time
from datetime import timedelta, datetime
from typing import Tuple, Optional, List

import pandas as pd

from ..core.exceptions import DataLoadingError, InvalidDataFormatError

logger = logging.getLogger(__name__)

def load_csv_to_dataframe(file_path: str, required_columns: Optional[List[str]] = None, **kwargs) -> pd.DataFrame:
    """
    Loads a CSV file into a pandas DataFrame with robust error handling
    and optional column validation.

    Args:
        file_path: The path to the CSV file.
        required_columns: An optional list of column names that must exist.
        **kwargs: Additional arguments for pd.read_csv (e.g., sep=',', encoding='utf-8').

    Returns:
        A pandas DataFrame with the CSV data.

    Raises:
        DataLoadingError: If the file is not found or is empty.
        InvalidDataFormatError: If required columns are missing.
    """
    logger.info(f"Attempting to load CSV from: {file_path}")
    try:
        df = pd.read_csv(file_path, **kwargs)
        
        if required_columns:
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                raise InvalidDataFormatError(
                    f"CSV file '{os.path.basename(file_path)}' does not contain required columns.",
                    file_path=file_path,
                    missing_columns=missing_cols
                )
        
        logger.info(f"CSV '{os.path.basename(file_path)}' loaded successfully with {len(df)} rows.")
        return df
        
    except FileNotFoundError:
        raise DataLoadingError(f"Data file not found at path: '{file_path}'.", file_path=file_path)
    except pd.errors.EmptyDataError:
        raise DataLoadingError(f"Data file '{os.path.basename(file_path)}' is empty.", file_path=file_path)
    except Exception as e:
        raise DataLoadingError(f"Unexpected error parsing CSV file '{file_path}': {e}", file_path=file_path) from e

### CHANGE HERE: The function name is now correct.
def cleanup_directory(
    target_dir: str,
    pattern: str = '*',
    max_age_hours: Optional[float] = None,
    log_prefix: str = ""
) -> Tuple[int, int]:
    """
    Robust utility to delete files matching a pattern within a directory,
    with an optional maximum age option.

    Args:
        target_dir: The directory where cleanup will be performed.
        pattern: The glob pattern to find files (e.g., '*.tmp', 'process_*.pkl').
        max_age_hours: If specified, only files older than this number of hours will be deleted.
        log_prefix: A prefix for log messages to provide context.

    Returns:
        A tuple with (files_deleted, errors_encountered).
    """
    if not target_dir or not os.path.isdir(target_dir):
        logger.error(f"{log_prefix} Directory for cleanup not found or invalid: {target_dir}")
        return 0, 1

    deleted_count, error_count = 0, 0
    now = time.time()
    
    if max_age_hours:
        cutoff_time = now - (max_age_hours * 3600)
        logger.info(f"{log_prefix} Cleaning files with pattern '{pattern}' in '{target_dir}' older than {max_age_hours} hours.")
    else:
        cutoff_time = None
        logger.info(f"{log_prefix} Cleaning all files with pattern '{pattern}' in '{target_dir}'.")

    try:
        for item_path in glob.glob(os.path.join(target_dir, pattern)):
            try:
                if os.path.isfile(item_path):
                    if cutoff_time is None or os.path.getmtime(item_path) < cutoff_time:
                        os.remove(item_path)
                        deleted_count += 1
                        logger.debug(f"{log_prefix} File deleted: {item_path}")
            except FileNotFoundError:
                logger.warning(f"{log_prefix} File not found during cleanup (already deleted?): {item_path}")
            except Exception as e:
                logger.error(f"{log_prefix} Error deleting file {item_path}: {e}")
                error_count += 1
    except Exception as e:
        logger.error(f"CRITICAL: Could not list directory '{target_dir}' for cleanup: {e}", exc_info=True)
        error_count += 1

    logger.info(f"{log_prefix} Cleanup completed. Deleted: {deleted_count}, Errors: {error_count}.")
    return deleted_count, error_count