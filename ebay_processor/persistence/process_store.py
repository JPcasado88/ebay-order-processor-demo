# ebay_processor/persistence/process_store.py
"""
Process State Persistence Module.

Contains the ProcessStore class, which is responsible for saving,
retrieving and managing the state of background processing jobs.

Uses the file system for persistence, saving each process state
in its own pickle file. This is suitable for stateless deployment environments
(like many cloud platforms) where process memory is not persistent.
"""

import logging
import os
import shutil
import pickle
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

# Reuse our directory cleanup utility
from ..utils.file_utils import cleanup_directory
from ..core.exceptions import OrderProcessingError

logger = logging.getLogger(__name__)

class ProcessStore:
    """
    Manages process state storage in pickle files.
    Write operations are atomic to prevent data corruption.
    """
    def __init__(self, storage_dir: str):
        """
        Initializes the process store.

        Args:
            storage_dir: The directory where state files will be saved.

        Raises:
            ValueError: If no storage directory is provided.
        """
        if not storage_dir:
            raise ValueError("A storage directory must be provided for ProcessStore.")
        
        self.storage_dir = storage_dir
        self.lock = threading.Lock()  # Lock to ensure thread-safe file operations.
        
        try:
            os.makedirs(storage_dir, exist_ok=True)
        except OSError as e:
            logger.critical(f"Could not create process storage directory: {storage_dir}. Error: {e}")
            raise OrderProcessingError(f"Failed to create storage directory: {e}") from e

    def _get_process_path(self, process_id: str) -> str:
        """Builds the full path to the file for a given process ID."""
        # Sanitize the process ID to prevent path traversal.
        # Only allow alphanumeric characters, underscores and dots.
        safe_filename = "".join(c for c in process_id if c.isalnum() or c in ['_', '.'])
        if not safe_filename:
            raise ValueError("Invalid or empty process ID.")
        return os.path.join(self.storage_dir, f"process_{safe_filename}.pkl")

    def get(self, process_id: str, default: Any = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves process information from its file.

        Args:
            process_id: The ID of the process to retrieve.
            default: The value to return if the process is not found.

        Returns:
            A dictionary with the process information, or the `default` value.
        """
        file_path = self._get_process_path(process_id)
        
        if not os.path.exists(file_path):
            return default
            
        try:
            # Make sure the file is not empty before attempting to read it.
            if os.path.getsize(file_path) > 0:
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            # If the file is empty, treat it as if it didn't exist.
            logger.warning(f"Process file {file_path} is empty. It will be deleted.")
            self.delete(process_id)
            return default
        except (EOFError, pickle.UnpicklingError) as e:
            logger.error(f"Error deserializing {file_path}. The file may be corrupted and will be deleted. Error: {e}")
            self.delete(process_id)
            return default
        except Exception as e:
            logger.error(f"Unrecoverable error reading process {process_id}: {e}", exc_info=True)
            return default

    def update(self, process_id: str, info: Dict[str, Any]):
        """
        Updates and saves process information to a file atomically.

        Uses a write to a temporary file and then renames it to avoid
        leaving a corrupted file if the process fails mid-write.

        Args:
            process_id: The ID of the process to update.
            info: The dictionary with the new process information.
        """
        with self.lock:
            file_path = self._get_process_path(process_id)
            temp_file_path = file_path + ".tmp"
            try:
                with open(temp_file_path, 'wb') as f:
                    pickle.dump(info, f, protocol=pickle.HIGHEST_PROTOCOL)
                # The 'move' operation is atomic on most operating systems.
                shutil.move(temp_file_path, file_path)
            except Exception as e:
                logger.error(f"Error updating process {process_id} to disk: {e}", exc_info=True)
                # Clean up the temporary file if the operation failed.
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError:
                        pass

    def delete(self, process_id: str) -> bool:
        """
        Deletes a process file from disk.

        Args:
            process_id: The ID of the process to delete.

        Returns:
            True if the file was deleted, False otherwise.
        """
        with self.lock:
            file_path = self._get_process_path(process_id)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Process file deleted: {file_path}")
                    return True
            except Exception as e:
                logger.error(f"Error deleting process file {file_path}: {e}", exc_info=True)
            return False

    def scheduled_cleanup(self, max_age_hours: int = 24):
        """
        Deletes process files that are older than a specified age.
        Designed to be called by a scheduler.
        """
        logger.info(f"Starting scheduled cleanup of process files older than {max_age_hours} hours.")
        cleanup_directory(
            target_dir=self.storage_dir,
            pattern='process_*.pkl',
            max_age_hours=max_age_hours,
            log_prefix="[ProcessStore Cleanup]"
        )