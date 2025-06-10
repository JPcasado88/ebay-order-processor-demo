# ebay_processor/utils/file_utils.py
"""
Módulo de Utilidades de Archivos y Sistema de Ficheros.

Proporciona funciones de ayuda para interactuar con el sistema de archivos,
como cargar datos desde ficheros, limpiar directorios y manejar rutas de
manera segura y con un logging adecuado.
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
    Carga un archivo CSV en un DataFrame de pandas con manejo de errores robusto
    y validación opcional de columnas.

    Args:
        file_path: La ruta al archivo CSV.
        required_columns: Una lista opcional de nombres de columna que deben existir.
        **kwargs: Argumentos adicionales para pd.read_csv (e.g., sep=',', encoding='utf-8').

    Returns:
        Un DataFrame de pandas con los datos del CSV.

    Raises:
        DataLoadingError: Si el archivo no se encuentra o está vacío.
        InvalidDataFormatError: Si faltan columnas requeridas.
    """
    logger.info(f"Intentando cargar CSV desde: {file_path}")
    try:
        df = pd.read_csv(file_path, **kwargs)
        
        if required_columns:
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                raise InvalidDataFormatError(
                    f"El archivo CSV '{os.path.basename(file_path)}' no contiene las columnas requeridas.",
                    file_path=file_path,
                    missing_columns=missing_cols
                )
        
        logger.info(f"CSV '{os.path.basename(file_path)}' cargado exitosamente con {len(df)} filas.")
        return df
        
    except FileNotFoundError:
        raise DataLoadingError(f"Archivo de datos no encontrado en la ruta: '{file_path}'.", file_path=file_path)
    except pd.errors.EmptyDataError:
        raise DataLoadingError(f"El archivo de datos '{os.path.basename(file_path)}' está vacío.", file_path=file_path)
    except Exception as e:
        raise DataLoadingError(f"Error inesperado al parsear el archivo CSV '{file_path}': {e}", file_path=file_path) from e

### CAMBIO AQUÍ: El nombre de la función ahora es el correcto.
def cleanup_directory(
    target_dir: str,
    pattern: str = '*',
    max_age_hours: Optional[float] = None,
    log_prefix: str = ""
) -> Tuple[int, int]:
    """
    Utilidad robusta para eliminar archivos que coinciden con un patrón dentro de un directorio,
    con una opción de antigüedad máxima.

    Args:
        target_dir: El directorio donde se realizará la limpieza.
        pattern: El patrón de glob para encontrar archivos (e.g., '*.tmp', 'process_*.pkl').
        max_age_hours: Si se especifica, solo se borrarán los archivos más antiguos que este número de horas.
        log_prefix: Un prefijo para los mensajes de log para dar contexto.

    Returns:
        Una tupla con (archivos_borrados, errores_encontrados).
    """
    if not target_dir or not os.path.isdir(target_dir):
        logger.error(f"{log_prefix} Directorio para limpieza no encontrado o inválido: {target_dir}")
        return 0, 1

    deleted_count, error_count = 0, 0
    now = time.time()
    
    if max_age_hours:
        cutoff_time = now - (max_age_hours * 3600)
        logger.info(f"{log_prefix} Limpiando archivos con patrón '{pattern}' en '{target_dir}' más antiguos de {max_age_hours} horas.")
    else:
        cutoff_time = None
        logger.info(f"{log_prefix} Limpiando todos los archivos con patrón '{pattern}' en '{target_dir}'.")

    try:
        for item_path in glob.glob(os.path.join(target_dir, pattern)):
            try:
                if os.path.isfile(item_path):
                    if cutoff_time is None or os.path.getmtime(item_path) < cutoff_time:
                        os.remove(item_path)
                        deleted_count += 1
                        logger.debug(f"{log_prefix} Archivo eliminado: {item_path}")
            except FileNotFoundError:
                logger.warning(f"{log_prefix} Archivo no encontrado durante la limpieza (ya borrado?): {item_path}")
            except Exception as e:
                logger.error(f"{log_prefix} Error al borrar el archivo {item_path}: {e}")
                error_count += 1
    except Exception as e:
        logger.error(f"CRÍTICO: No se pudo listar el directorio '{target_dir}' para limpieza: {e}", exc_info=True)
        error_count += 1

    logger.info(f"{log_prefix} Limpieza finalizada. Borrados: {deleted_count}, Errores: {error_count}.")
    return deleted_count, error_count