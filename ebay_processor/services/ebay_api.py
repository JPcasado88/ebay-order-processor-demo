# ebay_processor/services/ebay_api.py
"""
eBay API Interaction Service.

This module encapsulates all communication with the eBay Trading API.
It handles two main tasks:
1.  Managing OAuth2 authentication tokens, including automatic renewal.
2.  Making API calls to retrieve orders (`GetOrders`).

Functions are designed to be more pure, receiving the necessary configuration
as arguments to facilitate testing and decoupling.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import requests
from ebaysdk.exception import ConnectionError as EbayConnectionError
from ebaysdk.trading import Connection as Trading

# Import our custom exceptions
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

# --- Token Management ---

def refresh_oauth_token(app_id: str, cert_id: str, refresh_token: str, scopes: List[str]) -> Dict[str, Any]:
    """
    Refreshes an eBay OAuth2 access token using a refresh_token.

    Args:
        app_id: The eBay application App ID.
        cert_id: The eBay application Cert ID.
        refresh_token: The valid refresh token for the store account.
        scopes: The list of required scopes (e.g., "https://api.ebay.com/oauth/api_scope").

    Returns:
        A dictionary with the new 'access_token' and other response data.

    Raises:
        TokenRefreshError: If the eBay API request to refresh the token fails.
    """
    import base64

    # eBay requires credentials in Base64 format for this call.
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
        logger.info(f"Attempting to refresh token for refresh_token ending in '...{refresh_token[-4:]}'.")
        response = requests.post('https://api.ebay.com/identity/v1/oauth2/token', headers=headers, data=body)
        response.raise_for_status()  # Raises an exception for HTTP error codes (4xx or 5xx).
        
        token_data = response.json()
        logger.info(f"Token refreshed successfully for '...{refresh_token[-4:]}'.")
        return token_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error attempting to refresh token: {e}")
        raise TokenRefreshError(f"Network error during token refresh: {e}", store_id="Unknown")
    except Exception as e:
        logger.error(f"Unexpected error refreshing token: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
        raise TokenRefreshError(f"Unexpected error during token refresh: {e}", store_id="Unknown")


def check_and_refresh_tokens(
    app_id: str, 
    cert_id: str, 
    store_accounts: List[Dict[str, Any]], 
    token_file_path: str
) -> List[Dict[str, Any]]:
    """
    Checks the validity of tokens for each store account and refreshes them if necessary.

    This function reads a JSON token state file, checks the expiration date
    of each token, refreshes them if they're about to expire, and saves the new state to the file.

    Args:
        app_id: eBay API credential.
        cert_id: eBay API credential.
        store_accounts: The list of store accounts from configuration.
        token_file_path: The path to the JSON file where token state is persisted.

    Returns:
        The updated list of store accounts, with fresh access tokens.
    """
    try:
        with open(token_file_path, 'r') as f:
            token_state = json.load(f)
        logger.info(f"Token state file loaded from '{token_file_path}'.")
    except (FileNotFoundError, json.JSONDecodeError):
        token_state = {}
        logger.warning(f"Token file not found or could not be read. A new one will be created at '{token_file_path}'.")

    updated_accounts = []
    needs_save = False

    for account in store_accounts:
        store_id = account['account_id']
        refresh_token = account.get('refresh_token')
        
        if not refresh_token:
            logger.error(f"Store '{store_id}' does not have a configured refresh_token. It will be skipped.")
            continue

        store_token_info = token_state.get(store_id, {})
        expiry_str = store_token_info.get('expiry_time')
        
        # Determine if a refresh is needed.
        # Refresh if there's no token, no expiration date, or if it expires within 10 minutes.
        should_refresh = True
        if expiry_str:
            try:
                expiry_time = datetime.fromisoformat(expiry_str)
                if expiry_time > datetime.now(timezone.utc) + timedelta(minutes=10):
                    should_refresh = False
            except ValueError:
                logger.warning(f"Invalid expiration date format for '{store_id}'. Forcing refresh.")

        if should_refresh:
            logger.info(f"Token for store '{store_id}' needs to be refreshed.")
            try:
                new_token_data = refresh_oauth_token(
                    app_id, cert_id, refresh_token,
                    scopes=["https://api.ebay.com/oauth/api_scope"]
                )
                
                # Update state with the new token and new expiration date.
                account['access_token'] = new_token_data['access_token']
                expires_in_seconds = new_token_data.get('expires_in', 7200) # Default to 2 hours
                new_expiry_time = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
                
                token_state[store_id] = {
                    'access_token': new_token_data['access_token'],
                    'expiry_time': new_expiry_time.isoformat()
                }
                needs_save = True
                
            except TokenRefreshError as e:
                logger.critical(f"CRITICAL FAILURE refreshing token for store '{store_id}': {e}. This store cannot be processed.")
                # Skip this account but continue with others.
                continue
        else:
            # If the token is valid, simply use it from the saved state.
            account['access_token'] = store_token_info['access_token']
            logger.info(f"Token for store '{store_id}' is valid. No refresh needed.")

        updated_accounts.append(account)

    if needs_save:
        try:
            with open(token_file_path, 'w') as f:
                json.dump(token_state, f, indent=4)
            logger.info(f"Updated token state has been saved to '{token_file_path}'.")
        except IOError as e:
            logger.error(f"Could not save updated token state file: {e}")

    return updated_accounts


# --- Order Retrieval ---

def get_ebay_orders(
    api_connection: Trading,
    from_date: datetime,
    to_date: datetime,
    store_name: str,
) -> List[Any]:
    """
    Gets orders from an eBay store within a date range.
    Handles pagination automatically to get all results.

    Args:
        api_connection: An authenticated eBay Trading SDK instance.
        from_date: The start date (UTC) to search for orders.
        to_date: The end date (UTC) to search for orders.
        store_name: The store name, for logging.

    Returns:
        A list of order objects from the eBay SDK.

    Raises:
        EbayApiError: If the API call fails due to connection or API reasons.
    """
    all_orders = []
    page_number = 1
    
    # Format dates to the format expected by the eBay API.
    from_date_iso = from_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    to_date_iso = to_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    logger.info(f"[{store_name}] Searching for orders from {from_date_iso} to {to_date_iso}.")

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
            
            logger.info(f"[{store_name}] Making GetOrders call, Page: {page_number}.")
            response = api_connection.execute('GetOrders', api_call_params)

            # The SDK raises an exception if the response is not 'Success'.
            # But we do an extra check just in case.
            if response.reply.Ack != 'Success':
                errors = response.reply.Errors
                error_message = f"GetOrders call failed. Code: {errors[0].ErrorCode}, Message: {errors[0].LongMessage}"
                raise EbayApiError(error_message, store_id=store_name, api_call="GetOrders")

            orders_on_page = response.reply.OrderArray.Order if hasattr(response.reply.OrderArray, 'Order') else []
            if not isinstance(orders_on_page, list):
                orders_on_page = [orders_on_page]
            
            all_orders.extend(orders_on_page)
            logger.info(f"[{store_name}] Page {page_number}: {len(orders_on_page)} orders received. Total accumulated: {len(all_orders)}.")
            
            # Pagination logic
            if response.reply.HasMoreOrders == 'false':
                logger.info(f"[{store_name}] No more order pages. Ending search.")
                break
            
            page_number += 1
            if page_number > 50: # Safety limit to avoid infinite loops.
                logger.warning(f"[{store_name}] Reached limit of 50 pages. Stopping search.")
                break

        except EbayConnectionError as e:
            error_message = f"eBay API connection error when getting orders: {e}"
            logger.error(f"[{store_name}] {error_message}")
            raise EbayApiError(error_message, store_id=store_name, api_call="GetOrders")
        
        except Exception as e:
            # Catch any other unexpected error during the call.
            error_message = f"Unexpected error during GetOrders: {e}"
            logger.error(f"[{store_name}] {error_message}", exc_info=True)
            raise EbayApiError(error_message, store_id=store_name, api_call="GetOrders")

    logger.info(f"[{store_name}] Search completed. Total orders found: {len(all_orders)}.")
    return all_orders