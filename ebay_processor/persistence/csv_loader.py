# ebay_processor/persistence/csv_loader.py
"""
Módulo de Carga de Datos de Referencia (Catálogo).

Este módulo se encarga de la carga y preparación del archivo CSV maestro
(e.g., ktypemaster3.csv) que contiene el catálogo de productos.

La preparación incluye:
- Selección y validación de columnas requeridas.
- Renombrado de columnas para consistencia interna.
- Limpieza y normalización de datos para facilitar el matching.
- Creación de columnas derivadas para optimizar las búsquedas.
"""

import logging
import re
from datetime import datetime
import pandas as pd

# Utilidades para la carga de archivos y normalización de strings
from ..utils.file_utils import load_csv_to_dataframe
from ..utils.string_utils import normalize_ref_no
from ..core.exceptions import DataLoadingError
from ..core.constants import MasterDataColumns

logger = logging.getLogger(__name__)

def load_and_prepare_master_data(file_path: str) -> pd.DataFrame:
    """
    Carga y prepara el DataFrame del catálogo maestro desde un archivo CSV.

    Args:
        file_path: La ruta al archivo ktypemaster3.csv o similar.

    Returns:
        Un DataFrame de pandas limpio y listo para ser usado por el servicio de matching.

    Raises:
        DataLoadingError: Si el archivo no puede ser cargado o tiene un formato inválido.
    """
    logger.info(f"Iniciando carga y preparación de datos maestros desde: {file_path}")
    
    # Define las columnas que son absolutamente necesarias para que la app funcione.
    required_cols = [
        MasterDataColumns.TEMPLATE, MasterDataColumns.COMPANY, MasterDataColumns.MODEL,
        MasterDataColumns.YEAR, MasterDataColumns.MATS, MasterDataColumns.NUM_CLIPS,
        MasterDataColumns.CLIP_TYPE
    ]
    
    # Carga el CSV usando nuestra utilidad, que ya valida la existencia de las columnas.
    try:
        # Usamos `keep_default_na=False` para tratar celdas vacías como "" en lugar de NaN,
        # lo que simplifica el manejo de strings.
        df = load_csv_to_dataframe(
            file_path, 
            required_columns=required_cols,
            keep_default_na=False,
            dtype=str  # Cargar todo como string inicialmente para evitar errores de tipo.
        )
    except DataLoadingError as e:
        logger.error(f"No se pudo cargar el archivo de datos maestros: {e}", exc_info=True)
        raise

    # Columnas opcionales que se usarán si existen.
    optional_cols = [MasterDataColumns.FORCED_MATCH_SKU]
    
    # Crear una lista de todas las columnas a mantener.
    cols_to_keep = required_cols + [col for col in optional_cols if col in df.columns]
    
    # Usar una copia para evitar el SettingWithCopyWarning de pandas.
    df_cleaned = df[cols_to_keep].copy()
    
    # Renombrar columnas para consistencia interna en la aplicación.
    df_cleaned.rename(columns={MasterDataColumns.NUM_CLIPS: MasterDataColumns.INTERNAL_CLIP_COUNT}, inplace=True)
    
    # --- Limpieza y Normalización de Datos ---

    # Normalizar la columna YEAR: reemplazar "to present" por el año actual.
    current_year = str(datetime.now().year)
    df_cleaned[MasterDataColumns.YEAR] = df_cleaned[MasterDataColumns.YEAR].str.replace(
        r'to\s+present', f'-{current_year}', flags=re.IGNORECASE, regex=True
    )
    
    # Normalizar las columnas de texto clave: a minúsculas y sin espacios extra.
    text_cols_to_normalize = [
        MasterDataColumns.COMPANY, MasterDataColumns.MODEL, MasterDataColumns.YEAR,
        MasterDataColumns.CLIP_TYPE, MasterDataColumns.TEMPLATE
    ]
    for col in text_cols_to_normalize:
        df_cleaned[col] = df_cleaned[col].str.lower().str.strip()

    # --- Creación de Columnas Derivadas para Matching ---

    # Crear una columna 'Template_Normalized' para búsquedas rápidas y exactas.
    # Ej: "MS-123 AB" -> "MS123AB"
    df_cleaned[MasterDataColumns.NORMALIZED_TEMPLATE] = df_cleaned[MasterDataColumns.TEMPLATE].apply(normalize_ref_no)
    
    # Crear una columna normalizada para 'ForcedMatchSKU' si existe.
    if MasterDataColumns.FORCED_MATCH_SKU in df_cleaned.columns:
        df_cleaned['_normalized_forced_sku'] = df_cleaned[MasterDataColumns.FORCED_MATCH_SKU].str.strip().str.lower()

    logger.info(f"DataFrame maestro preparado. Total de filas: {len(df_cleaned)}. Columnas: {list(df_cleaned.columns)}")
    
    return df_cleaned