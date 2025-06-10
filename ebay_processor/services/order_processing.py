# ebay_processor/services/order_processing.py

import logging
import os
import shutil
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import zipfile
import pandas as pd 
from flask import current_app
from ebaysdk.trading import Connection as Trading
import pytz
from . import ebay_api, sku_matching, file_generation, color_extraction
from ..utils.date_utils import parse_ebay_datetime
from .barcode_service import BarcodeService
from ..persistence.process_store import ProcessStore
from ..persistence.csv_loader import load_and_prepare_master_data
from ..core.exceptions import OrderProcessingError, DataLoadingError, EbayApiError

logger = logging.getLogger(__name__)


class OrderProcessingService:
    def __init__(self, process_id: str, config: Dict[str, Any]):
        self.process_id = process_id
        self.config = config
        self.process_store = ProcessStore(config['PROCESS_STORE_DIR'])
        self.process_info = self.process_store.get(process_id)
        if not self.process_info:
            raise OrderProcessingError(f"No se pudo encontrar información para el process_id: {process_id}")
        
        self.barcode_service = BarcodeService(config['STORE_INITIALS'])
        from .car_details_extractor import CarDetailsExtractor
        self.car_details_extractor = CarDetailsExtractor()

    def _update_status(self, status: str, message: str, progress: int):
        self.process_info['status'] = status
        self.process_info['message'] = message
        self.process_info['progress'] = progress
        self.process_store.update(self.process_id, self.process_info)
        logger.info(f"Process [{self.process_id}]: {status} - {message} ({progress}%)")
    
    def _update_store_progress(self, store_id: str, status: str, message: str, orders_found: int = 0, page: int = None, max_pages: int = None):
        """Update progress information for a specific store."""
        if 'store_progress' not in self.process_info:
            self.process_info['store_progress'] = {}
        
        store_data = {
            'status': status,
            'message': message,
            'orders_found': orders_found
        }
        
        if page is not None:
            store_data['page'] = page
        if max_pages is not None:
            store_data['max_pages'] = max_pages
            
        self.process_info['store_progress'][store_id] = store_data
        self.process_store.update(self.process_id, self.process_info)

    def run_processing(self):
        try:
            self._update_status('processing', 'Cargando datos de referencia...', 5)
            form_data = self.process_info['form_data']
            
            try:
                matlist_df_cleaned = load_and_prepare_master_data(self.config['MATLIST_CSV_PATH'])
            except DataLoadingError as e:
                self._update_status('error', f"Error crítico al cargar datos: {e}", 5)
                raise

            self._update_status('processing', 'Verificando y refrescando tokens de eBay...', 15)
            refreshed_accounts = ebay_api.check_and_refresh_tokens(
                app_id=self.config['EBAY_APP_ID'],
                cert_id=self.config['EBAY_CERT_ID'],
                store_accounts=self.config['EBAY_STORE_ACCOUNTS'],
                token_file_path=self.config['EBAY_CONFIG_JSON_PATH']
            )

            all_expedited, all_standard, all_unmatched = [], [], []
            num_stores = len(refreshed_accounts)

            for i, store_account in enumerate(refreshed_accounts):
                store_id = store_account['account_id']
                progress = 20 + int((i / num_stores) * 50) if num_stores > 0 else 70
                self._update_status('processing', f"Procesando tienda: {store_id}...", progress)

                # Initialize store progress
                self._update_store_progress(store_id, 'processing', 'Iniciando procesamiento...', orders_found=0)

                try:
                    ### CAMBIO ###: La llamada a la función que procesa la tienda ahora está aquí.
                    processed_data = self._process_single_store(
                        store_account, matlist_df_cleaned, form_data
                    )
                    
                    # Calculate totals for this store
                    store_orders_found = len(processed_data['expedited']) + len(processed_data['standard']) + len(processed_data['unmatched'])
                    
                    all_expedited.extend(processed_data['expedited'])
                    all_standard.extend(processed_data['standard'])
                    all_unmatched.extend(processed_data['unmatched'])
                    
                    # Mark store as complete
                    self._update_store_progress(
                        store_id, 'complete', f"Completado - {store_orders_found} órdenes procesadas", 
                        orders_found=store_orders_found
                    )
                    
                except OrderProcessingError as e:
                    logger.error(f"Error procesando la tienda {store_id}: {e}", exc_info=True)
                    self.process_info.setdefault('store_errors', []).append(f"{store_id}: {e}")
                    # Mark store as error
                    self._update_store_progress(store_id, 'error', str(e), orders_found=0)
                    continue

            self.process_info['all_expedited_orders'] = all_expedited
            self.process_info['all_standard_orders'] = all_standard
            self.process_info['all_unmatched_items'] = all_unmatched

            self._update_status('processing', 'Asignando códigos de barras únicos...', 75)
            all_processed_items = all_expedited + all_standard
            run_date = datetime.now(timezone.utc)
            
            self.barcode_service.assign_base_barcodes(all_processed_items, run_date)
            self.barcode_service.assign_final_barcodes(all_processed_items)
            
            self._update_status('processing', 'Generando archivos de salida...', 85)
            temp_dir = self.process_info['temp_dir']
            output_files_requested = form_data.get('output_files', [])
            generated_file_paths = {}

            if 'run' in output_files_requested:
                path = file_generation.generate_consolidated_run_file(all_standard, temp_dir, run_date, self.config)
                if path: generated_file_paths[os.path.basename(path)] = path

            if 'run24h' in output_files_requested:
                path = file_generation.generate_run24h_file(all_expedited, temp_dir, run_date, self.config)
                if path: generated_file_paths[os.path.basename(path)] = path

            if 'courier_master' in output_files_requested:
                path = file_generation.generate_consolidated_courier_master_file(all_processed_items, temp_dir, run_date, self.config)
                if path: generated_file_paths[os.path.basename(path)] = path

            if 'tracking' in output_files_requested:
                paths = file_generation.generate_tracking_files(all_processed_items, temp_dir, run_date, self.config)
                for p in paths: generated_file_paths[os.path.basename(p)] = p

            if all_unmatched:
                path = file_generation.generate_unmatched_items_file(all_unmatched, temp_dir, run_date, self.config)
                if path: generated_file_paths[os.path.basename(path)] = path
            
            self._update_status('processing', 'Finalizando y archivando...', 95)
            persistent_output_dir = self.config['OUTPUT_DIR']
            
            for filename, temp_path in generated_file_paths.items():
                dest_path = os.path.join(persistent_output_dir, filename)
                shutil.move(temp_path, dest_path)
                generated_file_paths[filename] = dest_path

            zip_filename = f"ebay_orders_{run_date.strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(persistent_output_dir, zip_filename)
            
            # Crear ZIP de forma segura
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for filename, path in generated_file_paths.items():
                    if os.path.exists(path):
                        zf.write(path, filename)

            self.process_info['generated_file_paths'] = generated_file_paths
            # Only include files that actually exist and determine their types
            generated_files_with_types = []
            for filename, path in generated_file_paths.items():
                if os.path.exists(path):
                    file_type = self._determine_file_type(filename)
                    generated_files_with_types.append({'name': filename, 'type': file_type})
            
            self.process_info['generated_files'] = generated_files_with_types
            self.process_info['zip_file'] = {'name': zip_filename, 'path': zip_path}
            self.process_info['completion_time_iso'] = datetime.now(timezone.utc).isoformat()
            
            self._update_status('complete', '¡Proceso completado!', 100)

        except Exception as e:
            logger.error(f"Error fatal en el proceso de fondo [{self.process_id}]: {e}", exc_info=True)
            self._update_status('error', f'Error inesperado: {e}', self.process_info.get('progress', 0))
        
        finally:
            temp_dir = self.process_info.get('temp_dir')
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Directorio temporal [{temp_dir}] eliminado.")
                except Exception as cleanup_err:
                    logger.error(f"Error al eliminar el directorio temporal [{temp_dir}]: {cleanup_err}")

    ### CAMBIO ###: Esta es la función que movimos aquí. Es un método privado de la clase.
    def _process_single_store(self, store_account: Dict, matlist_df: pd.DataFrame, form_data: Dict) -> Dict[str, List]:
        store_id = store_account['account_id']
        access_token = store_account.get('access_token')
        
        # Check if we're in demo mode
        if self.config.get('DEMO_MODE', False):
            logger.info(f"[DEMO MODE] Processing store: {store_id}")
            return self._process_single_store_demo(store_account, matlist_df, form_data)
        
        if not access_token:
            logger.error(f"La tienda {store_id} no tiene token de acceso. Omitiendo.")
            return {'expedited': [], 'standard': [], 'unmatched': []}

        api_conn = Trading(
            appid=self.config['EBAY_APP_ID'],
            certid=self.config['EBAY_CERT_ID'],
            devid=self.config['EBAY_DEV_ID'],
            token=access_token,
            config_file=None,
            siteid='3'
        )

        from_date = datetime.fromisoformat(self.process_info['from_dt_iso'])
        to_date = datetime.now(timezone.utc)
        
        try:
            # Update store progress during API call
            self._update_store_progress(store_id, 'processing', 'Obteniendo pedidos de eBay...', orders_found=0)
            raw_orders = ebay_api.get_ebay_orders(api_conn, from_date, to_date, store_id)
            self._update_store_progress(store_id, 'processing', f'Procesando {len(raw_orders)} pedidos...', orders_found=len(raw_orders))
        except EbayApiError as e:
            raise OrderProcessingError(f"Fallo al obtener pedidos para {store_id}: {e}") from e

        all_processed_items, unmatched_items = [], []
        order_item_counts = {}

        logger.info(f"[{store_id}] Iniciando procesamiento de {len(raw_orders)} órdenes con filtros: include_all_orders={form_data.get('include_all_orders', False)}, next_24h_only={form_data.get('next_24h_only', False)}")
        
        processed_count = 0
        skipped_dispatched = 0
        skipped_not_urgent = 0
        
        for order in raw_orders:
            order_id = getattr(order, 'OrderID', 'Unknown')
            
            # Filtro 1: Omitir pedidos según el checkbox 'Include Dispatched'
            if self._should_skip_order(order, form_data.get('include_all_orders', False)):
                skipped_dispatched += 1
                logger.debug(f"[{store_id}] Orden {order_id} omitida: ya despachada")
                continue
            
            # Filtro 2: Si el checkbox '24h only' está marcado, omitir si no es urgente.
            if form_data.get('next_24h_only', False):
                is_urgent = self._is_shipping_due(order)
                logger.debug(f"[{store_id}] Orden {order_id} es urgente: {is_urgent}")
                if not is_urgent:
                    skipped_not_urgent += 1
                    logger.debug(f"[{store_id}] Orden {order_id} omitida: no es urgente (no debe despacharse en 24h)")
                    continue

            transactions = getattr(order.TransactionArray, 'Transaction', [])
            if not isinstance(transactions, list):
                transactions = [transactions]
            
            processed_count += 1
            
            for txn in transactions:
                item_data = self._process_transaction(txn, order, matlist_df, store_id)
                if item_data:
                    all_processed_items.extend(item_data)
                else:
                    unmatched_items.append(self._create_unmatched_item(txn, order, store_id))
        
        logger.info(f"[{store_id}] Resumen de filtrado: {processed_count} procesadas, {skipped_dispatched} omitidas (ya despachadas), {skipped_not_urgent} omitidas (no urgentes)")
        
        for item in all_processed_items:
            order_id = item['ORDER ID']
            order_item_counts[order_id] = order_item_counts.get(order_id, 0) + 1
            
        expedited, standard = self._categorize_orders(all_processed_items, order_item_counts)
        
        return {'expedited': expedited, 'standard': standard, 'unmatched': unmatched_items}

    def _process_single_store_demo(self, store_account: Dict, matlist_df: pd.DataFrame, form_data: Dict) -> Dict[str, List]:
        """
        Demo mode version of _process_single_store that uses mock data instead of real eBay API calls.
        This preserves all the processing logic while using demo data.
        """
        store_id = store_account['account_id']
        logger.info(f"[DEMO MODE] Processing demo data for store: {store_id}")
        
        from_date = datetime.fromisoformat(self.process_info['from_dt_iso'])
        to_date = datetime.now(timezone.utc)
        
        # Update store progress during mock API call
        self._update_store_progress(store_id, 'processing', '[DEMO] Obteniendo pedidos de eBay...', orders_found=0)
        
        # Get demo orders instead of real API call
        raw_orders = ebay_api.get_demo_orders(store_id, from_date, to_date)
        
        # Convert demo orders to the same format as real eBay orders for processing
        demo_orders = self._convert_demo_orders_to_ebay_format(raw_orders)
        
        self._update_store_progress(store_id, 'processing', f'[DEMO] Procesando {len(demo_orders)} pedidos...', orders_found=len(demo_orders))

        all_processed_items, unmatched_items = [], []
        order_item_counts = {}

        logger.info(f"[DEMO MODE] [{store_id}] Iniciando procesamiento de {len(demo_orders)} órdenes con filtros: include_all_orders={form_data.get('include_all_orders', False)}, next_24h_only={form_data.get('next_24h_only', False)}")
        
        processed_count = 0
        skipped_dispatched = 0
        skipped_not_urgent = 0
        
        for order in demo_orders:
            order_id = getattr(order, 'OrderID', 'Unknown')
            
            # Apply the same filtering logic as real orders
            if self._should_skip_order(order, form_data.get('include_all_orders', False)):
                skipped_dispatched += 1
                logger.debug(f"[DEMO MODE] [{store_id}] Orden {order_id} omitida: ya despachada")
                continue
            
            if form_data.get('next_24h_only', False):
                is_urgent = self._is_shipping_due(order)
                logger.debug(f"[DEMO MODE] [{store_id}] Orden {order_id} es urgente: {is_urgent}")
                if not is_urgent:
                    skipped_not_urgent += 1
                    logger.debug(f"[DEMO MODE] [{store_id}] Orden {order_id} omitida: no es urgente")
                    continue

            transactions = getattr(order.TransactionArray, 'Transaction', [])
            if not isinstance(transactions, list):
                transactions = [transactions]
            
            processed_count += 1
            
            for txn in transactions:
                item_data = self._process_transaction(txn, order, matlist_df, store_id)
                if item_data:
                    all_processed_items.extend(item_data)
                else:
                    unmatched_items.append(self._create_unmatched_item(txn, order, store_id))
        
        logger.info(f"[DEMO MODE] [{store_id}] Resumen de filtrado: {processed_count} procesadas, {skipped_dispatched} omitidas (ya despachadas), {skipped_not_urgent} omitidas (no urgentes)")
        
        for item in all_processed_items:
            order_id = item['ORDER ID']
            order_item_counts[order_id] = order_item_counts.get(order_id, 0) + 1
            
        expedited, standard = self._categorize_orders(all_processed_items, order_item_counts)
        
        return {'expedited': expedited, 'standard': standard, 'unmatched': unmatched_items}

    def _convert_demo_orders_to_ebay_format(self, demo_orders: List[Dict]) -> List:
        """
        Convert demo order dictionaries to mock eBay order objects for processing compatibility.
        This creates objects that behave like eBay SDK objects but contain demo data.
        """
        from types import SimpleNamespace
        
        converted_orders = []
        for demo_order in demo_orders:
            # Create mock eBay order object
            order = SimpleNamespace()
            order.OrderID = demo_order['OrderID']
            order.CreatedTime = demo_order['CreatedTime']
            order.OrderTotal = demo_order['OrderTotal']
            order.BuyerUserID = demo_order['BuyerUserID']
            order.OrderStatus = 'Complete'
            order.CheckoutStatus = SimpleNamespace()
            order.CheckoutStatus.Status = 'Complete'
            order.CheckoutStatus.eBayPaymentStatus = 'NoPaymentFailure'
            order.PaymentHoldStatus = ''
            order.ShippedTime = None  # Demo orders are not shipped yet
            order.BuyerCheckoutMessage = 'Demo order for presentation purposes'
            
            # Create shipping address
            addr_data = demo_order['ShippingAddress']
            order.ShippingAddress = SimpleNamespace()
            order.ShippingAddress.Name = addr_data['Name']
            order.ShippingAddress.Street1 = addr_data['Street1']
            order.ShippingAddress.Street2 = ''
            order.ShippingAddress.CityName = addr_data['CityName']
            order.ShippingAddress.PostalCode = addr_data['PostalCode']
            order.ShippingAddress.Country = addr_data['Country']
            order.ShippingAddress.Phone = '01234567890'
            
            # Create shipping service
            order.ShippingServiceSelected = SimpleNamespace()
            order.ShippingServiceSelected.ShippingService = 'Hermes'
            order.ShippingServiceSelected.ShippingServiceCost = SimpleNamespace()
            order.ShippingServiceSelected.ShippingServiceCost.value = '2.99'
            
            # Create buyer info
            order.Buyer = SimpleNamespace()
            order.Buyer.Email = f"{demo_order['BuyerUserID']}@demo-email.com"
            
            # Create transaction array
            order.TransactionArray = SimpleNamespace()
            transactions = []
            
            for item_data in demo_order['TransactionArray']['Transaction']:
                txn = SimpleNamespace()
                txn.TransactionID = item_data['TransactionID']
                txn.QuantityPurchased = item_data['QuantityPurchased']
                txn.TransactionPrice = item_data['TransactionPrice']
                
                # Create item
                txn.Item = SimpleNamespace()
                txn.Item.ItemID = item_data['Item']['ItemID']
                txn.Item.Title = item_data['Item']['Title']
                txn.Item.SKU = item_data['Item']['SKU']
                
                # No variation for demo orders (keep it simple)
                txn.Variation = None
                
                transactions.append(txn)
            
            order.TransactionArray.Transaction = transactions
            converted_orders.append(order)
        
        return converted_orders

    ### CAMBIO ###: Nuevas funciones de ayuda privadas para mantener el código limpio.
    def _process_transaction(self, txn: Any, order: Any, matlist_df: pd.DataFrame, store_id: str) -> Optional[List[Dict]]:
        item = getattr(txn, 'Item', None)
        if not item: return None

        # Handle both variation and non-variation items safely
        variation = getattr(txn, 'Variation', None)
        if variation:
            sku = getattr(variation, 'SKU', None) or getattr(item, 'SKU', 'SKU_NOT_FOUND')
        else:
            sku = getattr(item, 'SKU', 'SKU_NOT_FOUND')
        title = getattr(item, 'Title', 'Title not available')
        
        car_details = self.car_details_extractor.extract(title)
        
        match_data = sku_matching.find_best_match(sku, title, matlist_df, car_details)
        
        if not match_data:
            return None
            
        qty = int(getattr(txn, 'QuantityPurchased', 1))
        processed_items = []
        for _ in range(qty):
            item_dict = self._create_processed_item_dict(order, txn, match_data, store_id, sku, title)
            processed_items.append(item_dict)
        return processed_items

    def _create_processed_item_dict(self, order, txn, match_data, store_id, sku, title) -> Dict:
        shipping_info = self._get_shipping_address(order)
        full_name = getattr(order.ShippingAddress, 'Name', '')
        first_name, last_name = (full_name.split(' ', 1) + [''])[:2]
        buyer_email = ''
        if hasattr(order, 'Buyer') and order.Buyer:
            buyer_email = getattr(order.Buyer, 'Email', '')
        
        carpet, trim = color_extraction.extract_carpet_and_trim_colors(title)
        carpet_type = color_extraction.determine_carpet_type(title)
        embroidery = color_extraction.determine_embroidery_type(title)

        return {
            "ORDER ID": getattr(order, 'OrderID', ''),
            "Item Number": getattr(txn.Item, 'ItemID', ''),
            "Transaction ID": getattr(txn, 'TransactionID', ''),
            "Store ID": store_id,
            "FILE NAME": f"EBAY_ORDER_{getattr(order, 'OrderID', '')}_{datetime.now().strftime('%Y%m%d')}",
            "Process DATE": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            "FIRST NAME": first_name,
            "LAST NAME": last_name,
            "ADD1": shipping_info.get('Street1', ''),
            "ADD2": shipping_info.get('Street2', ''),
            "ADD3": shipping_info.get('City', ''),
            "ADD4": shipping_info.get('Country', ''),
            "POSTCODE": shipping_info.get('Postal Code', ''),
            "TEL NO": shipping_info.get('Phone', ''),
            "EMAIL ADDRESS": buyer_email, # <<< Usamos nuestra variable segura
            "QTY": '1',
            "Product Title": title,
            "Raw SKU": sku,
            "REF NO": match_data.get('Template', ''),
            "TRIM": trim,
            "CARPET TYPE": carpet_type,
            "CARPET COLOUR": carpet,
            "Embroidery": embroidery,
            "Make": match_data.get('COMPANY', ''),
            "Model": match_data.get('MODEL', ''),
            "YEAR": match_data.get('YEAR', ''),
            "Pcs/Set": match_data.get('MATS', ''),
            "NO OF CLIPS": match_data.get('NO OF CLIPS', ''),
            "CLIP TYPE": match_data.get('Type', ''),
            "SERVICE": getattr(order.ShippingServiceSelected, 'ShippingService', 'Hermes'),
            "Delivery Special Instruction": getattr(order, 'BuyerCheckoutMessage', ''),
            "_shipping_cost": float(getattr(order.ShippingServiceSelected.ShippingServiceCost, 'value', 0.0))
        }

    
    def _should_skip_order(self, order: Any, include_all_orders: bool) -> bool:
        """
        Comprueba si un pedido debe ser omitido basado en su estado.
        Esta es una emulación completa de la lógica de filtrado original.
        """
        order_id = getattr(order, 'OrderID', 'Unknown')
        
        # 1. Comprobación de estado general del pedido
        status = getattr(order, 'OrderStatus', '').lower()
        cancel_status = getattr(order, 'CancelStatus', '').lower()
        if status in ['cancelled', 'inactive', 'invalid'] or 'cancel' in cancel_status:
            logger.debug(f"[{order_id}] Omitido por estado de cancelación: {status}/{cancel_status}")
            return True
            
        # 2. Comprobación del estado del pago y checkout
        checkout = getattr(order, 'CheckoutStatus', None)
        if checkout:
            if getattr(checkout, 'Status', '').lower() != 'complete':
                logger.debug(f"[{order_id}] Omitido por checkout no completado.")
                return True
            
            payment_status = getattr(checkout, 'eBayPaymentStatus', '').lower()
            # Omitir si el pago no se ha completado o está en proceso.
            # 'NoPaymentFailure' significa que el pago fue exitoso o no aplica.
            if payment_status not in ['nopaymentfailure', 'paymentreceived', '']:
                logger.debug(f"[{order_id}] Omitido por estado de pago: {payment_status}")
                return True

        # 3. Comprobación de retención de pago
        if getattr(order, 'PaymentHoldStatus', '') == 'PaymentHold':
            logger.debug(f"[{order_id}] Omitido por pago retenido (PaymentHold).")
            return True

        # 4. Comprobación de si ya fue despachado (solo si el checkbox no está marcado)
        if not include_all_orders and getattr(order, 'ShippedTime', None):
            logger.debug(f"[{order_id}] Omitido: ya despachado y no se incluyen todos.")
            return True
            
        # Si pasa todos los filtros, no se omite.
        return False
    
    def _is_shipping_due(self, order: Any) -> bool:
        """Comprueba si un pedido debe ser enviado en las próximas 24 horas hábiles."""
        uk_timezone = pytz.timezone('Europe/London')
        current_date_uk = datetime.now(uk_timezone).date()
        order_id = getattr(order, 'OrderID', 'Unknown')
        
        logger.debug(f"[{order_id}] Evaluando urgencia de envío. Fecha actual UK: {current_date_uk}")
        
        # Comprobar por 'ExpectedShipDate'
        expected_ship_date_str = getattr(order, 'ExpectedShipDate', None)
        logger.debug(f"[{order_id}] ExpectedShipDate raw: {expected_ship_date_str}")
        
        if expected_ship_date_str:
            expected_ship_date = parse_ebay_datetime(expected_ship_date_str)
            if expected_ship_date:
                expected_date_uk = expected_ship_date.astimezone(uk_timezone).date()
                logger.debug(f"[{order_id}] ExpectedShipDate procesado: {expected_date_uk}")
                if expected_date_uk <= current_date_uk:
                    logger.info(f"Pedido {order_id} es URGENTE (por ExpectedShipDate: {expected_date_uk}).")
                    return True
                else:
                    logger.debug(f"[{order_id}] No urgente por ExpectedShipDate: {expected_date_uk} > {current_date_uk}")
                
        # Comprobar por 'PaidTime' y 'DispatchTimeMax'
        paid_time_str = getattr(order, 'PaidTime', None)
        logger.debug(f"[{order_id}] PaidTime raw: {paid_time_str}")
        
        if paid_time_str:
            paid_time = parse_ebay_datetime(paid_time_str)
            if paid_time:
                paid_time_uk = paid_time.astimezone(uk_timezone)
                dispatch_days = 1 # Por defecto
                
                if hasattr(order, 'ShippingDetails') and getattr(order.ShippingDetails, 'DispatchTimeMax', None):
                    try:
                        dispatch_days = int(order.ShippingDetails.DispatchTimeMax)
                    except (ValueError, TypeError):
                        pass
                
                logger.debug(f"[{order_id}] PaidTime: {paid_time_uk.date()}, DispatchTimeMax: {dispatch_days} días")
                
                # Calcular la fecha de envío (solo días laborables)
                ship_by_date = paid_time_uk.date()
                days_added = 0
                while days_added < dispatch_days:
                    ship_by_date += timedelta(days=1)
                    if ship_by_date.weekday() < 5: # Lunes=0, Viernes=4
                        days_added += 1

                logger.debug(f"[{order_id}] Fecha calculada de envío: {ship_by_date}")
                
                if ship_by_date <= current_date_uk:
                    logger.info(f"Pedido {order_id} es URGENTE (por fecha de envío calculada: {ship_by_date}).")
                    return True
                else:
                    logger.debug(f"[{order_id}] No urgente por fecha calculada: {ship_by_date} > {current_date_uk}")
                    
        logger.debug(f"[{order_id}] Pedido NO es urgente (sin ExpectedShipDate ni PaidTime válidos)")
        return False

    def _get_shipping_address(self, order: Any) -> Dict:
        addr = order.ShippingAddress
        return {
            "Street1": getattr(addr, 'Street1', ''),
            "Street2": getattr(addr, 'Street2', ''),
            "City": getattr(addr, 'CityName', ''),
            "Country": getattr(addr, 'Country', ''),
            "Postal Code": getattr(addr, 'PostalCode', ''),
            "Phone": getattr(addr, 'Phone', '')
        }
    
    def _create_unmatched_item(self, txn, order, store_id) -> Dict:
        # Handle both variation and non-variation items safely
        variation = getattr(txn, 'Variation', None)
        if variation:
            sku = getattr(variation, 'SKU', None) or getattr(txn.Item, 'SKU', 'SKU_NOT_FOUND')
        else:
            sku = getattr(txn.Item, 'SKU', 'SKU_NOT_FOUND')
        title = getattr(txn.Item, 'Title', 'Title not available')
        return {
            "SKU": sku, 
            "Product Title": title, 
            "OrderID": getattr(order, 'OrderID', 'N/A'), 
            "Store ID": store_id,
            "Error": "No match found in catalog"
        }

    def _categorize_orders(self, all_items: List, counts: Dict) -> tuple[List, List]:
        expedited, standard = [], []
        for item in all_items:
            order_id = item['ORDER ID']
            shipping_cost = item.pop('_shipping_cost', 0.0)
            item['Shipping Cost'] = shipping_cost
            
            is_expedited = shipping_cost > 0 or counts.get(order_id, 1) > 1
            if is_expedited:
                expedited.append(item)
            else:
                standard.append(item)
        return expedited, standard
    
    def _determine_file_type(self, filename: str) -> str:
        """Determine the file type based on filename patterns."""
        filename_lower = filename.lower()
        if 'run_consolidated' in filename_lower:
            return 'Standard Orders (RUN)'
        elif 'run24h' in filename_lower:
            return 'Express Orders (RUN24H)'
        elif 'courier_master' in filename_lower:
            return 'Courier Master'
        elif 'tracking' in filename_lower:
            if 'consolidated' in filename_lower:
                return 'Tracking (All Stores)'
            else:
                return 'Tracking (Individual Store)'
        elif 'unmatched' in filename_lower:
            return 'Unmatched Items'
        elif 'duplicates' in filename_lower:
            return 'Duplicate Orders'
        else:
            return 'Generated File'

def start_order_processing_thread(app, process_id: str):
    with app.app_context():
        logger.info(f"Iniciando hilo de procesamiento para el process_id: {process_id}")
        try:
            service = OrderProcessingService(process_id, current_app.config)
            service.run_processing()
        except Exception as e:
            logger.critical(f"No se pudo iniciar OrderProcessingService para [{process_id}]: {e}", exc_info=True)
            store = ProcessStore(current_app.config.get('PROCESS_STORE_DIR'))
            if store:
                info = store.get(process_id, {})
                info['status'] = 'error'
                info['message'] = f'Fallo de inicialización: {e}'
                store.update(process_id, info)