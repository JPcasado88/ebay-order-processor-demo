# ebay_processor/core/exceptions.py
"""
Módulo de Excepciones Personalizadas.

Define clases de excepción específicas para el dominio de la aplicación.
Esto permite un manejo de errores más granular y significativo en toda la base de código.
En lugar de capturar un `ValueError` genérico, podemos capturar un `SKUMatchingError`
y saber exactamente qué tipo de problema ocurrió.
"""

class OrderProcessingError(Exception):
    """
    Excepción base para todos los errores relacionados con el procesamiento de órdenes.
    Permite capturar cualquier error de nuestro dominio con un solo `except`.
    """
    def __init__(self, message, **kwargs):
        super().__init__(message)
        self.details = kwargs

    def __str__(self):
        base_message = super().__str__()
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{base_message} (Detalles: {details_str})"
        return base_message


class EbayApiError(OrderProcessingError):
    """
    Se lanza cuando hay un problema durante la comunicación con la API de eBay.
    """
    def __init__(self, message, store_id=None, api_call=None):
        super().__init__(message, store_id=store_id, api_call=api_call)
        self.store_id = store_id
        self.api_call = api_call


class TokenRefreshError(EbayApiError):
    """
    Excepción específica para cuando falla la renovación de un token de OAuth2.
    """
    def __init__(self, message, store_id):
        super().__init__(message, store_id=store_id, api_call="refresh_token")


class DataLoadingError(OrderProcessingError):
    """
    Se lanza cuando hay un problema al cargar archivos de datos de referencia (e.g., ktypemaster3.csv).
    """
    def __init__(self, message, file_path=None):
        super().__init__(message, file_path=file_path)
        self.file_path = file_path


class InvalidDataFormatError(DataLoadingError):
    """
    Se lanza cuando un archivo de datos se carga correctamente pero le faltan
    columnas requeridas o tiene un formato inesperado.
    """
    def __init__(self, message, file_path=None, missing_columns=None):
        super().__init__(message, file_path=file_path, missing_columns=missing_columns)
        self.missing_columns = missing_columns


class SKUMatchingError(OrderProcessingError):
    """
    Se lanza cuando el motor de emparejamiento no puede encontrar una coincidencia
    o encuentra un estado ambiguo.
    """
    def __init__(self, message, sku=None, product_title=None, order_id=None):
        super().__init__(message, sku=sku, product_title=product_title, order_id=order_id)
        self.sku = sku
        self.product_title = product_title
        self.order_id = order_id


class FileGenerationError(OrderProcessingError):
    """
    Se lanza cuando ocurre un error durante la creación o escritura de un archivo de salida.
    """
    def __init__(self, message, filename=None, sheet_name=None):
        super().__init__(message, filename=filename, sheet_name=sheet_name)
        self.filename = filename
        self.sheet_name = sheet_name


class BarcodeGenerationError(OrderProcessingError):
    """
    Se lanza si ocurre un problema durante la asignación de códigos de barras.
    """
    def __init__(self, message, order_id=None):
        super().__init__(message, order_id=order_id)
        self.order_id = order_id


class ConfigurationError(Exception):
    """
    Excepción separada para problemas de configuración de la aplicación (e.g., variables de entorno faltantes).
    No hereda de OrderProcessingError porque suele ocurrir al inicio y no durante el procesamiento.
    """
    pass