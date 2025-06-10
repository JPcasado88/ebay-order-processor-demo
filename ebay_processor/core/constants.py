# ebay_processor/core/constants.py
"""
Módulo de Constantes del Negocio.

Este archivo centraliza todas las constantes, "valores mágicos" y
configuraciones estáticas utilizadas a lo largo de la aplicación.
Hacer esto mejora la mantenibilidad y la claridad del código, ya que
la lógica de negocio clave se define en un solo lugar.
"""

from typing import Set, Tuple

# --- eBay API ---
EBAY_SITE_ID_UK = '3'  # Corresponde al sitio de eBay Reino Unido.
UK_TIMEZONE = 'Europe/London'  # Timezone para cálculos de fechas de envío en UK.

# --- Envío y Courier ---
DEFAULT_COURIER = "Hermes"
DEFAULT_BARCODE_TYPE = "CODE93"
NEXT_DAY_SERVICE_NAME = "UK NEXT DAY DELIVERY"
STANDARD_SERVICE_NAME = "UK STANDARD DELIVERY"

# Prefijos de códigos postales que usualmente tienen un servicio de envío diferente
# o más lento (e.g., Highlands, Islands). Se usa para determinar el tipo de servicio.
# Es una tupla para un chequeo `startswith` eficiente.
HIGHLANDS_AND_ISLANDS_POSTCODES: Tuple[str, ...] = (
    'BT', 'IV', 'AB', 'KA27', 'KA28', 'PA20', 'PA38', 'PA41', 'PA42', 'PA43', 'PA44',
    'PA45', 'PA46', 'PA47', 'PA48', 'PA49', 'PA60', 'PA61', 'PA62', 'PA63', 'PA64',
    'PA65', 'PA66', 'PA67', 'PA68', 'PA69', 'PA70', 'PA71', 'PA72', 'PA73', 'PA74',
    'PA75', 'PA76', 'PA77', 'PA78', 'PH17', 'PH18', 'PH19', 'PH20', 'PH21', 'PH22',
    'PH23', 'PH24', 'PH25', 'PH26', 'PH30', 'PH31', 'PH32', 'PH33', 'PH34', 'PH35',
    'PH36', 'PH37', 'PH38', 'PH39', 'PH40', 'PH41', 'PH42', 'PH43', 'PH44', 'PH49',
    'PH50', 'HS', 'ZE', 'IM', 'GY', 'JE', 'KW'
)

# --- Atributos de Producto ---

# Un set para búsquedas rápidas (`if color in ALLOWED_COLORS:`).
# Centraliza todos los colores reconocidos por el sistema.
ALLOWED_COLORS: Set[str] = {
    'red', 'blue', 'green', 'grey', 'silver', 'yellow', 'white',
    'orange', 'purple', 'brown', 'pink', 'black', 'beige', 'tan'
}

# Tipos de alfombra reconocidos. Usado para estandarizar la salida.
class Carpet:
    VELOUR = 'CTVEL'
    RUBBER_STD = 'RUBSTD'
    RUBBER_HD = 'RUBHD'
    STANDARD = 'CT65'

# --- ¡CLASE AÑADIDA! ---
# Tipos de bordado reconocidos.
class Embroidery:
    DOUBLE_STITCH = "Double Stitch"
    NONE = ""

# --- Nombres de Archivos y Hojas de Cálculo ---
INFO_HEADER_TAG = "#INFO" # Etiqueta usada en la primera fila de algunos archivos de tracking.
UNMATCHED_SHEET_TITLE = "Unmatched Items"
TRACKING_SHEET_TITLE = "Tracking"
RUN_SHEET_TITLE = "RUN"
RUN24H_SHEET_TITLE = "RUN24H"
COURIER_MASTER_SHEET_TITLE = "COURIER_MASTER"


# --- Columnas Clave de DataFrames (para consistencia entre servicios) ---
# Usadas para asegurar que los DataFrames siempre tengan las columnas requeridas
# antes de ser procesados o generados.
class MasterDataColumns:
    TEMPLATE = 'Template'
    COMPANY = 'COMPANY'
    MODEL = 'MODEL'
    YEAR = 'YEAR'
    MATS = 'MATS'
    NUM_CLIPS = '#Clips'
    CLIP_TYPE = 'Type'
    FORCED_MATCH_SKU = 'ForcedMatchSKU'
    
    # Columnas renombradas internamente
    INTERNAL_CLIP_COUNT = 'NO OF CLIPS'
    
    # Columnas normalizadas/generadas para procesamiento
    NORMALIZED_TEMPLATE = 'Template_Normalized'