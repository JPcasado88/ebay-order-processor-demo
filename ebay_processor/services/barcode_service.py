# ebay_processor/services/barcode_service.py
"""
Barcode Generation Service.

This service encapsulates all the logic for creating unique barcodes
for each item in an order. It's designed to be instantiated once
per order processing execution, ensuring that counters
and states are fresh for each new batch.

Implements a two-pass system:
1.  **Base Assignment:** Each item is assigned a globally unique base barcode
    within the execution.
2.  **Final Assignment:** Base codes are reviewed and numeric suffixes
    are added to items that belong to orders with multiple products,
    ensuring that each individual product has an absolutely unique final
    barcode for picking.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BarcodeService:
    """
    Manages barcode generation for a single processing execution.
    """
    def __init__(self, store_initials_map: Dict[str, str]):
        """
        Initializes the barcode service.

        Args:
            store_initials_map: A dictionary that maps store_id to their initials.
                                E.g., {'MyStoreUK': 'MS', 'AnotherStore': 'AS'}.
        """
        if not store_initials_map:
            logger.warning("Store initials map is empty. Fallbacks will be used.")
        self.store_initials_map = store_initials_map
        self._row_counter = 1  # Counter that increments for each generated base code.
        logger.info("BarcodeService instantiated and state reset.")

    def _get_next_row_id(self) -> int:
        """Gets the next unique row number for a barcode."""
        current_id = self._row_counter
        self._row_counter += 1
        return current_id

    def _generate_base_barcode(self, store_id: str, date: datetime) -> str:
        """
        Generates a unique base barcode in the format: INITIALS+COUNTER+DATE.
        This is the "base" code before applying suffixes for multiple items.

        Args:
            store_id: The store ID to get the initials.
            date: The order date to format in the code.

        Returns:
            The generated base barcode (e.g., "MS001230724").
        """
        # Gets store initials from the map, with a safe fallback.
        initials = self.store_initials_map.get(store_id, store_id[:2].upper() if store_id else 'XX')
        
        row_num = self._get_next_row_id()
        date_str = date.strftime('%d%m%y')
        
        # Format the row number to 3 digits (001, 012, 123) for consistency.
        return f"{initials}{row_num:03d}{date_str}"

    def assign_base_barcodes(self, all_items: List[Dict[str, Any]], run_date: datetime):
        """
        First pass: Assigns a base barcode to each item in the list.
        Modifies item dictionaries in place, adding the 'AssignedBaseBarcode' key.

        Args:
            all_items: List of dictionaries, where each represents a processed item.
            run_date: The current execution date to embed in the barcode.
        """
        logger.info(f"Starting Pass 1: Assigning base barcodes to {len(all_items)} items.")
        for item in all_items:
            store_id = item.get('Store ID')
            if not store_id:
                logger.error(f"Item with Order ID {item.get('ORDER ID')} has no 'Store ID'. Cannot generate barcode.")
                item['AssignedBaseBarcode'] = None
                continue
            
            base_barcode = self._generate_base_barcode(store_id, run_date)
            item['AssignedBaseBarcode'] = base_barcode
        logger.info("Pass 1 completed.")

    def assign_final_barcodes(self, all_items: List[Dict[str, Any]]):
        """
        Second pass: Processes base barcodes and assigns a final unique barcode
        to each item, adding suffixes if necessary.
        Modifies items in place, adding the 'FinalBarcode' key.

        Args:
            all_items: The same item list, already processed by `assign_base_barcodes`.
        """
        logger.info(f"Starting Pass 2: Assigning final barcodes to {len(all_items)} items.")
        
        # Group items by their Order ID to identify orders with multiple products.
        order_groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in all_items:
            order_id = item.get('ORDER ID')
            if order_id:
                order_groups.setdefault(order_id, []).append(item)
            else:
                # Anomalous case: an item without Order ID cannot be processed correctly.
                item['FinalBarcode'] = item.get('AssignedBaseBarcode') # Assign the base as fallback
                logger.warning(f"Item without Order ID found. Cannot apply suffix logic.")

        for order_id, items_in_order in order_groups.items():
            if len(items_in_order) == 1:
                # If there's only one item in the order, the final code is the same as the base.
                item = items_in_order[0]
                item['FinalBarcode'] = item.get('AssignedBaseBarcode')
            else:
                # If there are multiple items, add a numeric suffix to each one.
                # Sort by SKU so suffixes are consistent between executions.
                sorted_items = sorted(items_in_order, key=lambda x: x.get('Raw SKU', ''))
                for i, item in enumerate(sorted_items):
                    base_barcode = item.get('AssignedBaseBarcode')
                    suffix = f"{i + 1:02d}"  # Two-digit suffix: 01, 02, etc.
                    item['FinalBarcode'] = f"{base_barcode}{suffix}"
                    logger.debug(f"Multi-item order {order_id}: Assigned {item['FinalBarcode']} to SKU {item.get('Raw SKU')}")
        
        logger.info("Pass 2 completed.")