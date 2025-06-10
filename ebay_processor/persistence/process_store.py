# ebay_processor/persistence/process_store.py
"""
Módulo de Persistencia de Estado de Procesos.

Contiene la clase ProcessStore, que es responsable de guardar,
recuperar y gestionar el estado de los trabajos de procesamiento en segundo plano.

Utiliza el sistema de archivos para la persistencia, guardando cada estado de
proceso en su propio archivo pickle. Esto es adecuado para entornos de despliegue
sin estado (como muchas plataformas en la nube) donde la memoria del proceso no es persistente.
"""

import logging
import os
import shutil
import pickle
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

# Reutilizamos nuestra utilidad de limpieza de directorios
from ..utils.file_utils import cleanup_directory
from ..core.exceptions import OrderProcessingError

logger = logging.getLogger(__name__)

class ProcessStore:
    """
    Gestiona el almacenamiento del estado de los procesos en archivos pickle.
    Las operaciones de escritura son atómicas para prevenir la corrupción de datos.
    """
    def __init__(self, storage_dir: str):
        """
        Inicializa el almacén de procesos.

        Args:
            storage_dir: El directorio donde se guardarán los archivos de estado.

        Raises:
            ValueError: Si no se proporciona un directorio de almacenamiento.
        """
        if not storage_dir:
            raise ValueError("Se debe proporcionar un directorio de almacenamiento para ProcessStore.")
        
        self.storage_dir = storage_dir
        self.lock = threading.Lock()  # Lock para asegurar operaciones de archivo seguras entre hilos.
        
        try:
            os.makedirs(storage_dir, exist_ok=True)
        except OSError as e:
            logger.critical(f"No se pudo crear el directorio de almacenamiento de procesos: {storage_dir}. Error: {e}")
            raise OrderProcessingError(f"Fallo al crear el directorio de almacenamiento: {e}") from e

    def _get_process_path(self, process_id: str) -> str:
        """Construye la ruta completa al archivo para un ID de proceso dado."""
        # Sanear el ID del proceso para evitar path traversal.
        # Solo permite caracteres alfanuméricos, guiones bajos y puntos.
        safe_filename = "".join(c for c in process_id if c.isalnum() or c in ['_', '.'])
        if not safe_filename:
            raise ValueError("ID de proceso inválido o vacío.")
        return os.path.join(self.storage_dir, f"process_{safe_filename}.pkl")

    def get(self, process_id: str, default: Any = None) -> Optional[Dict[str, Any]]:
        """
        Recupera la información de un proceso desde su archivo.

        Args:
            process_id: El ID del proceso a recuperar.
            default: El valor a devolver si el proceso no se encuentra.

        Returns:
            Un diccionario con la información del proceso, o el valor `default`.
        """
        file_path = self._get_process_path(process_id)
        
        if not os.path.exists(file_path):
            return default
            
        try:
            # Asegurarse de que el archivo no esté vacío antes de intentar leerlo.
            if os.path.getsize(file_path) > 0:
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            # Si el archivo está vacío, tratarlo como si no existiera.
            logger.warning(f"El archivo de proceso {file_path} está vacío. Será eliminado.")
            self.delete(process_id)
            return default
        except (EOFError, pickle.UnpicklingError) as e:
            logger.error(f"Error al deserializar {file_path}. El archivo puede estar corrupto y será eliminado. Error: {e}")
            self.delete(process_id)
            return default
        except Exception as e:
            logger.error(f"Error irrecuperable al leer el proceso {process_id}: {e}", exc_info=True)
            return default

    def update(self, process_id: str, info: Dict[str, Any]):
        """
        Actualiza y guarda la información de un proceso en un archivo de forma atómica.

        Utiliza una escritura en un archivo temporal y luego lo renombra para evitar
        dejar un archivo corrupto si el proceso falla a mitad de la escritura.

        Args:
            process_id: El ID del proceso a actualizar.
            info: El diccionario con la nueva información del proceso.
        """
        with self.lock:
            file_path = self._get_process_path(process_id)
            temp_file_path = file_path + ".tmp"
            try:
                with open(temp_file_path, 'wb') as f:
                    pickle.dump(info, f, protocol=pickle.HIGHEST_PROTOCOL)
                # La operación 'move' es atómica en la mayoría de los sistemas operativos.
                shutil.move(temp_file_path, file_path)
            except Exception as e:
                logger.error(f"Error al actualizar el proceso {process_id} en disco: {e}", exc_info=True)
                # Limpiar el archivo temporal si la operación falló.
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError:
                        pass

    def delete(self, process_id: str) -> bool:
        """
        Elimina el archivo de un proceso del disco.

        Args:
            process_id: El ID del proceso a eliminar.

        Returns:
            True si el archivo fue eliminado, False en caso contrario.
        """
        with self.lock:
            file_path = self._get_process_path(process_id)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Archivo de proceso eliminado: {file_path}")
                    return True
            except Exception as e:
                logger.error(f"Error al eliminar el archivo de proceso {file_path}: {e}", exc_info=True)
            return False

    def scheduled_cleanup(self, max_age_hours: int = 24):
        """
        Elimina los archivos de proceso que son más antiguos que una edad determinada.
        Diseñado para ser llamado por un planificador (scheduler).
        """
        logger.info(f"Iniciando limpieza programada de archivos de proceso más antiguos de {max_age_hours} horas.")
        cleanup_directory(
            target_dir=self.storage_dir,
            pattern='process_*.pkl',
            max_age_hours=max_age_hours,
            log_prefix="[ProcessStore Cleanup]"
        )