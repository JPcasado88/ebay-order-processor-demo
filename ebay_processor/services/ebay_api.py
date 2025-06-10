# ebay_processor/services/ebay_api.py
"""
Servicio de Interacción con la API de eBay.

Este módulo encapsula toda la comunicación con la API de eBay Trading.
Se encarga de dos tareas principales:
1.  Gestionar los tokens de autenticación OAuth2, incluyendo su renovación automática.
2.  Realizar llamadas a la API para obtener pedidos (`GetOrders`).

Las funciones están diseñadas para ser más puras, recibiendo la configuración
necesaria como argumentos para facilitar las pruebas y el desacoplamiento.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import requests
from ebaysdk.exception import ConnectionError as EbayConnectionError
from ebaysdk.trading import Connection as Trading

# Importamos nuestras excepciones personalizadas
from ..core.exceptions import EbayApiError, TokenRefreshError
from ..utils.date_utils import parse_ebay_datetime

# Demo mode support
from .demo_data import DemoDataService

logger = logging.getLogger(__name__)

# --- Demo Mode Functions ---

def get_demo_orders(store_name: str, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
    """
    Returns demo orders for the specified store and date range.
    This function is used when DEMO_MODE is enabled.
    """
    logger.info(f"[DEMO MODE] Getting demo orders for store '{store_name}' from {from_date} to {to_date}")
    
    demo_service = DemoDataService()
    
    # Calculate days back from to_date for filtering
    days_back = (to_date - from_date).days + 1
    
    # Get demo orders for this store
    demo_orders = demo_service.get_sample_orders(store_name, days_back)
    
    # Convert to eBay-like order format for compatibility
    converted_orders = []
    for order in demo_orders:
        converted_order = {
            'OrderID': order['OrderID'],
            'CreatedTime': order['CreatedTime'],
            'OrderTotal': order['OrderTotal'],
            'BuyerUserID': order['BuyerName'].replace(' ', '').lower(),
            'ShippingAddress': order['BuyerAddress'],
            'TransactionArray': {
                'Transaction': []
            }
        }
        
        # Convert items to eBay transaction format
        for item in order['Items']:
            transaction = {
                'Item': {
                    'ItemID': item['ItemID'],
                    'Title': item['Title'],
                    'SKU': item['SKU']
                },
                'TransactionID': f"{item['ItemID']}-001",
                'QuantityPurchased': item['Quantity'],
                'TransactionPrice': item['Price']
            }
            converted_order['TransactionArray']['Transaction'].append(transaction)
        
        converted_orders.append(converted_order)
    
    logger.info(f"[DEMO MODE] Returning {len(converted_orders)} demo orders for store '{store_name}'")
    return converted_orders

# --- Gestión de Tokens ---

def refresh_oauth_token(app_id: str, cert_id: str, refresh_token: str, scopes: List[str]) -> Dict[str, Any]:
    """
    Refresca un token de acceso OAuth2 de eBay usando un refresh_token.

    Args:
        app_id: El App ID de la aplicación de eBay.
        cert_id: El Cert ID de la aplicación de eBay.
        refresh_token: El refresh token válido para la cuenta de la tienda.
        scopes: La lista de scopes requeridos (e.g., "https://api.ebay.com/oauth/api_scope").

    Returns:
        Un diccionario con el nuevo 'access_token' y otros datos de la respuesta.

    Raises:
        TokenRefreshError: Si la solicitud a la API de eBay para refrescar el token falla.
    """
    import base64

    # eBay requiere las credenciales en formato Base64 para esta llamada.
    auth_header = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {auth_header}'
    }
    body = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'scope': ' '.join(scopes)
    }

    try:
        logger.info(f"Intentando refrescar token para el refresh_token que termina en '...{refresh_token[-4:]}'.")
        response = requests.post('https://api.ebay.com/identity/v1/oauth2/token', headers=headers, data=body)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP (4xx o 5xx).
        
        token_data = response.json()
        logger.info(f"Token refrescado exitosamente para '...{refresh_token[-4:]}'.")
        return token_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red al intentar refrescar el token: {e}")
        raise TokenRefreshError(f"Error de red durante el refresco del token: {e}", store_id="Desconocido")
    except Exception as e:
        logger.error(f"Error inesperado al refrescar el token: {e}. Respuesta: {response.text if 'response' in locals() else 'N/A'}")
        raise TokenRefreshError(f"Error inesperado durante el refresco del token: {e}", store_id="Desconocido")


def check_and_refresh_tokens(
    app_id: str, 
    cert_id: str, 
    store_accounts: List[Dict[str, Any]], 
    token_file_path: str
) -> List[Dict[str, Any]]:
    """
    Verifica la validez de los tokens para cada cuenta de tienda y los refresca si es necesario.

    Esta función lee un archivo JSON de estado de tokens, comprueba la fecha de expiración
    de cada uno, los refresca si están a punto de expirar, y guarda el nuevo estado en el archivo.

    Args:
        app_id: Credencial de la API de eBay.
        cert_id: Credencial de la API de eBay.
        store_accounts: La lista de cuentas de tienda desde la configuración.
        token_file_path: La ruta al archivo JSON donde se persiste el estado de los tokens.

    Returns:
        La lista actualizada de cuentas de tienda, con los tokens de acceso frescos.
    """
    try:
        with open(token_file_path, 'r') as f:
            token_state = json.load(f)
        logger.info(f"Archivo de estado de tokens cargado desde '{token_file_path}'.")
    except (FileNotFoundError, json.JSONDecodeError):
        token_state = {}
        logger.warning(f"No se encontró o no se pudo leer el archivo de tokens. Se creará uno nuevo en '{token_file_path}'.")

    updated_accounts = []
    needs_save = False

    for account in store_accounts:
        store_id = account['account_id']
        refresh_token = account.get('refresh_token')
        
        if not refresh_token:
            logger.error(f"La tienda '{store_id}' no tiene un refresh_token configurado. Se omitirá.")
            continue

        store_token_info = token_state.get(store_id, {})
        expiry_str = store_token_info.get('expiry_time')
        
        # Determinar si se necesita un refresco.
        # Se refresca si no hay token, no hay fecha de expiración, o si expira en menos de 10 minutos.
        should_refresh = True
        if expiry_str:
            try:
                expiry_time = datetime.fromisoformat(expiry_str)
                if expiry_time > datetime.now(timezone.utc) + timedelta(minutes=10):
                    should_refresh = False
            except ValueError:
                logger.warning(f"Formato de fecha de expiración inválido para '{store_id}'. Forzando refresco.")

        if should_refresh:
            logger.info(f"El token para la tienda '{store_id}' necesita ser refrescado.")
            try:
                new_token_data = refresh_oauth_token(
                    app_id, cert_id, refresh_token,
                    scopes=["https://api.ebay.com/oauth/api_scope"]
                )
                
                # Actualizar el estado con el nuevo token y la nueva fecha de expiración.
                account['access_token'] = new_token_data['access_token']
                expires_in_seconds = new_token_data.get('expires_in', 7200) # Default a 2 horas
                new_expiry_time = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
                
                token_state[store_id] = {
                    'access_token': new_token_data['access_token'],
                    'expiry_time': new_expiry_time.isoformat()
                }
                needs_save = True
                
            except TokenRefreshError as e:
                logger.critical(f"FALLO CRÍTICO al refrescar el token para la tienda '{store_id}': {e}. Esta tienda no podrá ser procesada.")
                # Omitimos esta cuenta pero continuamos con las demás.
                continue
        else:
            # Si el token es válido, simplemente lo usamos del estado guardado.
            account['access_token'] = store_token_info['access_token']
            logger.info(f"El token para la tienda '{store_id}' es válido. No se necesita refresco.")

        updated_accounts.append(account)

    if needs_save:
        try:
            with open(token_file_path, 'w') as f:
                json.dump(token_state, f, indent=4)
            logger.info(f"El estado de los tokens actualizado se ha guardado en '{token_file_path}'.")
        except IOError as e:
            logger.error(f"No se pudo guardar el archivo de estado de tokens actualizado: {e}")

    return updated_accounts


# --- Obtención de Pedidos ---

def get_ebay_orders(
    api_connection: Trading,
    from_date: datetime,
    to_date: datetime,
    store_name: str,
) -> List[Any]:
    """
    Obtiene los pedidos de una tienda de eBay en un rango de fechas.
    Maneja la paginación automáticamente para obtener todos los resultados.

    Args:
        api_connection: Una instancia del SDK de eBay Trading ya autenticada.
        from_date: La fecha de inicio (UTC) para buscar pedidos.
        to_date: La fecha de fin (UTC) para buscar pedidos.
        store_name: El nombre de la tienda, para logging.

    Returns:
        Una lista de objetos de pedido del SDK de eBay.

    Raises:
        EbayApiError: Si la llamada a la API falla por razones de conexión o de la API.
    """
    all_orders = []
    page_number = 1
    
    # Formatear fechas al formato que espera la API de eBay.
    from_date_iso = from_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    to_date_iso = to_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    logger.info(f"[{store_name}] Buscando pedidos desde {from_date_iso} hasta {to_date_iso}.")

    while True:
        try:
            api_call_params = {
                'CreateTimeFrom': from_date_iso,
                'CreateTimeTo': to_date_iso,
                'OrderStatus': 'Completed',
                'OrderingRole': 'Seller',
                'Pagination': {
                    'EntriesPerPage': 100,
                    'PageNumber': page_number
                }
            }
            
            logger.info(f"[{store_name}] Realizando llamada a GetOrders, Página: {page_number}.")
            response = api_connection.execute('GetOrders', api_call_params)

            # El SDK lanza una excepción si la respuesta no es 'Success'.
            # Pero hacemos una comprobación extra por si acaso.
            if response.reply.Ack != 'Success':
                errors = response.reply.Errors
                error_message = f"La llamada a GetOrders falló. Código: {errors[0].ErrorCode}, Mensaje: {errors[0].LongMessage}"
                raise EbayApiError(error_message, store_id=store_name, api_call="GetOrders")

            orders_on_page = response.reply.OrderArray.Order if hasattr(response.reply.OrderArray, 'Order') else []
            if not isinstance(orders_on_page, list):
                orders_on_page = [orders_on_page]
            
            all_orders.extend(orders_on_page)
            logger.info(f"[{store_name}] Página {page_number}: {len(orders_on_page)} pedidos recibidos. Total acumulado: {len(all_orders)}.")
            
            # Lógica de paginación
            if response.reply.HasMoreOrders == 'false':
                logger.info(f"[{store_name}] No hay más páginas de pedidos. Finalizando búsqueda.")
                break
            
            page_number += 1
            if page_number > 50: # Límite de seguridad para evitar bucles infinitos.
                logger.warning(f"[{store_name}] Se alcanzó el límite de 50 páginas. Deteniendo la búsqueda.")
                break

        except EbayConnectionError as e:
            error_message = f"Error de conexión con la API de eBay al obtener pedidos: {e}"
            logger.error(f"[{store_name}] {error_message}")
            raise EbayApiError(error_message, store_id=store_name, api_call="GetOrders")
        
        except Exception as e:
            # Captura cualquier otro error inesperado durante la llamada.
            error_message = f"Error inesperado durante GetOrders: {e}"
            logger.error(f"[{store_name}] {error_message}", exc_info=True)
            raise EbayApiError(error_message, store_id=store_name, api_call="GetOrders")

    logger.info(f"[{store_name}] Búsqueda completada. Total de pedidos encontrados: {len(all_orders)}.")
    return all_orders