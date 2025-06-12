# ebay_processor/core/constants.py
"""
Business Constants Module.

This file centralizes all constants, "magic values" and
static configurations used throughout the application.
Doing this improves maintainability and code clarity, as
key business logic is defined in a single place.
"""

from typing import Set, Tuple

# --- eBay API ---
EBAY_SITE_ID_UK = '3'  # Corresponds to eBay UK site.
UK_TIMEZONE = 'Europe/London'  # Timezone for shipping date calculations in UK.

# --- Shipping and Courier ---
DEFAULT_COURIER = "Hermes"
DEFAULT_BARCODE_TYPE = "CODE93"
NEXT_DAY_SERVICE_NAME = "UK NEXT DAY DELIVERY"
STANDARD_SERVICE_NAME = "UK STANDARD DELIVERY"

# Postcode prefixes that usually have a different shipping service
# or slower delivery (e.g., Highlands, Islands). Used to determine service type.
# It's a tuple for efficient `startswith` checking.
HIGHLANDS_AND_ISLANDS_POSTCODES: Tuple[str, ...] = (
    'BT', 'IV', 'AB', 'KA27', 'KA28', 'PA20', 'PA38', 'PA41', 'PA42', 'PA43', 'PA44',
    'PA45', 'PA46', 'PA47', 'PA48', 'PA49', 'PA60', 'PA61', 'PA62', 'PA63', 'PA64',
    'PA65', 'PA66', 'PA67', 'PA68', 'PA69', 'PA70', 'PA71', 'PA72', 'PA73', 'PA74',
    'PA75', 'PA76', 'PA77', 'PA78', 'PH17', 'PH18', 'PH19', 'PH20', 'PH21', 'PH22',
    'PH23', 'PH24', 'PH25', 'PH26', 'PH30', 'PH31', 'PH32', 'PH33', 'PH34', 'PH35',
    'PH36', 'PH37', 'PH38', 'PH39', 'PH40', 'PH41', 'PH42', 'PH43', 'PH44', 'PH49',
    'PH50', 'HS', 'ZE', 'IM', 'GY', 'JE', 'KW'
)

# --- Product Attributes ---

# A set for fast lookups (`if color in ALLOWED_COLORS:`).
# Centralizes all colors recognized by the system.
ALLOWED_COLORS: Set[str] = {
    'red', 'blue', 'green', 'grey', 'silver', 'yellow', 'white',
    'orange', 'purple', 'brown', 'pink', 'black', 'beige', 'tan'
}

# Recognized carpet types. Used to standardize output.
class Carpet:
    VELOUR = 'CTVEL'
    RUBBER_STD = 'RUBSTD'
    RUBBER_HD = 'RUBHD'
    STANDARD = 'CT65'

# --- ADDED CLASS! ---
# Recognized embroidery types.
class Embroidery:
    DOUBLE_STITCH = "Double Stitch"
    NONE = ""

# --- File Names and Spreadsheets ---
INFO_HEADER_TAG = "#INFO"  # Tag used in the first row of some tracking files.
UNMATCHED_SHEET_TITLE = "Unmatched Items"
TRACKING_SHEET_TITLE = "Tracking"
RUN_SHEET_TITLE = "RUN"
RUN24H_SHEET_TITLE = "RUN24H"
COURIER_MASTER_SHEET_TITLE = "COURIER_MASTER"


# --- Key DataFrame Columns (for consistency between services) ---
# Used to ensure DataFrames always have the required columns
# before being processed or generated.
class MasterDataColumns:
    TEMPLATE = 'Template'
    COMPANY = 'COMPANY'
    MODEL = 'MODEL'
    YEAR = 'YEAR'
    MATS = 'MATS'
    NUM_CLIPS = '#Clips'
    CLIP_TYPE = 'Type'
    FORCED_MATCH_SKU = 'ForcedMatchSKU'
    
    # Internally renamed columns
    INTERNAL_CLIP_COUNT = 'NO OF CLIPS'
    
    # Normalized/generated columns for processing
    NORMALIZED_TEMPLATE = 'Template_Normalized'