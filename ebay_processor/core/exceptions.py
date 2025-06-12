# ebay_processor/core/exceptions.py
"""
Custom Exceptions Module.

Defines application domain-specific exception classes.
This allows for more granular and meaningful error handling throughout the codebase.
Instead of catching a generic `ValueError`, we can catch a `SKUMatchingError`
and know exactly what type of problem occurred.
"""

class OrderProcessingError(Exception):
    """
    Base exception for all order processing related errors.
    Allows catching any error from our domain with a single `except`.
    """
    def __init__(self, message, **kwargs):
        super().__init__(message)
        self.details = kwargs

    def __str__(self):
        base_message = super().__str__()
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{base_message} (Details: {details_str})"
        return base_message


class EbayApiError(OrderProcessingError):
    """
    Raised when there's a problem during communication with the eBay API.
    """
    def __init__(self, message, store_id=None, api_call=None):
        super().__init__(message, store_id=store_id, api_call=api_call)
        self.store_id = store_id
        self.api_call = api_call


class TokenRefreshError(EbayApiError):
    """
    Specific exception for when OAuth2 token refresh fails.
    """
    def __init__(self, message, store_id):
        super().__init__(message, store_id=store_id, api_call="refresh_token")


class DataLoadingError(OrderProcessingError):
    """
    Raised when there's a problem loading reference data files (e.g., ktypemaster3.csv).
    """
    def __init__(self, message, file_path=None):
        super().__init__(message, file_path=file_path)
        self.file_path = file_path


class InvalidDataFormatError(DataLoadingError):
    """
    Raised when a data file loads successfully but is missing
    required columns or has an unexpected format.
    """
    def __init__(self, message, file_path=None, missing_columns=None):
        super().__init__(message, file_path=file_path, missing_columns=missing_columns)
        self.missing_columns = missing_columns


class SKUMatchingError(OrderProcessingError):
    """
    Raised when the matching engine cannot find a match
    or encounters an ambiguous state.
    """
    def __init__(self, message, sku=None, product_title=None, order_id=None):
        super().__init__(message, sku=sku, product_title=product_title, order_id=order_id)
        self.sku = sku
        self.product_title = product_title
        self.order_id = order_id


class FileGenerationError(OrderProcessingError):
    """
    Raised when an error occurs during output file creation or writing.
    """
    def __init__(self, message, filename=None, sheet_name=None):
        super().__init__(message, filename=filename, sheet_name=sheet_name)
        self.filename = filename
        self.sheet_name = sheet_name


class BarcodeGenerationError(OrderProcessingError):
    """
    Raised if a problem occurs during barcode assignment.
    """
    def __init__(self, message, order_id=None):
        super().__init__(message, order_id=order_id)
        self.order_id = order_id


class ConfigurationError(Exception):
    """
    Separate exception for application configuration problems (e.g., missing environment variables).
    Doesn't inherit from OrderProcessingError because it usually occurs at startup, not during processing.
    """
    pass