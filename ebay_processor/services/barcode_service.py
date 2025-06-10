# ebay_processor/services/barcode_service.py
"""
Servicio de Generación de Códigos de Barras.

Este servicio encapsula toda la lógica para crear códigos de barras únicos
para cada ítem de un pedido. Está diseñado para ser instanciado una vez
por cada ejecución de procesamiento de órdenes, garantizando que los contadores
y estados sean frescos para cada nuevo lote.

Implementa un sistema de dos pasadas:
1.  **Asignación de Base:** A cada ítem se le asigna un código de barras base
    único globalmente dentro de la ejecución.
2.  **Asignación Final:** Se revisan los códigos base y se añaden sufijos
    numéricos a los ítems que pertenecen a pedidos con múltiples productos,
    asegurando que cada producto individual tenga un código de barras final
    absolutamente único para el picking.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BarcodeService:
    """
    Gestiona la generación de códigos de barras para una única ejecución de procesamiento.
    """
    def __init__(self, store_initials_map: Dict[str, str]):
        """
        Inicializa el servicio de códigos de barras.

        Args:
            store_initials_map: Un diccionario que mapea store_id a sus iniciales.
                                E.g., {'MyStoreUK': 'MS', 'AnotherStore': 'AS'}.
        """
        if not store_initials_map:
            logger.warning("El mapa de iniciales de tiendas está vacío. Se usarán fallbacks.")
        self.store_initials_map = store_initials_map
        self._row_counter = 1  # Contador que se incrementa por cada código base generado.
        logger.info("BarcodeService instanciado y estado reiniciado.")

    def _get_next_row_id(self) -> int:
        """Obtiene el siguiente número de fila único para un código de barras."""
        current_id = self._row_counter
        self._row_counter += 1
        return current_id

    def _generate_base_barcode(self, store_id: str, date: datetime) -> str:
        """
        Genera un código de barras base único en el formato: INICIALES+CONTADOR+FECHA.
        Este es el código "base" antes de aplicar sufijos para múltiples ítems.

        Args:
            store_id: El ID de la tienda para obtener las iniciales.
            date: La fecha de la orden para formatear en el código.

        Returns:
            El código de barras base generado (e.g., "MS001230724").
        """
        # Obtiene las iniciales de la tienda del mapa, con un fallback seguro.
        initials = self.store_initials_map.get(store_id, store_id[:2].upper() if store_id else 'XX')
        
        row_num = self._get_next_row_id()
        date_str = date.strftime('%d%m%y')
        
        # Formatea el número de fila a 3 dígitos (001, 012, 123) para consistencia.
        return f"{initials}{row_num:03d}{date_str}"

    def assign_base_barcodes(self, all_items: List[Dict[str, Any]], run_date: datetime):
        """
        Primera pasada: Asigna un código de barras base a cada ítem en la lista.
        Modifica los diccionarios de ítems en su lugar, añadiendo la clave 'AssignedBaseBarcode'.

        Args:
            all_items: Lista de diccionarios, donde cada uno representa un ítem procesado.
            run_date: La fecha de la ejecución actual para embeber en el código de barras.
        """
        logger.info(f"Iniciando Pasada 1: Asignando códigos de barras base a {len(all_items)} ítems.")
        for item in all_items:
            store_id = item.get('Store ID')
            if not store_id:
                logger.error(f"Ítem con Order ID {item.get('ORDER ID')} no tiene 'Store ID'. No se puede generar barcode.")
                item['AssignedBaseBarcode'] = None
                continue
            
            base_barcode = self._generate_base_barcode(store_id, run_date)
            item['AssignedBaseBarcode'] = base_barcode
        logger.info("Pasada 1 completada.")

    def assign_final_barcodes(self, all_items: List[Dict[str, Any]]):
        """
        Segunda pasada: Procesa los códigos de barras base y asigna un código de barras
        final y único a cada ítem, añadiendo sufijos si es necesario.
        Modifica los ítems en su lugar, añadiendo la clave 'FinalBarcode'.

        Args:
            all_items: La misma lista de ítems, ya procesada por `assign_base_barcodes`.
        """
        logger.info(f"Iniciando Pasada 2: Asignando códigos de barras finales a {len(all_items)} ítems.")
        
        # Agrupa los ítems por su Order ID para identificar pedidos con múltiples productos.
        order_groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in all_items:
            order_id = item.get('ORDER ID')
            if order_id:
                order_groups.setdefault(order_id, []).append(item)
            else:
                # Caso anómalo: un ítem sin Order ID no puede ser procesado correctamente.
                item['FinalBarcode'] = item.get('AssignedBaseBarcode') # Asignar el base como fallback
                logger.warning(f"Ítem sin Order ID encontrado. No se puede aplicar lógica de sufijos.")

        for order_id, items_in_order in order_groups.items():
            if len(items_in_order) == 1:
                # Si solo hay un ítem en el pedido, el código final es el mismo que el base.
                item = items_in_order[0]
                item['FinalBarcode'] = item.get('AssignedBaseBarcode')
            else:
                # Si hay múltiples ítems, se añade un sufijo numérico a cada uno.
                # Se ordena por SKU para que los sufijos sean consistentes entre ejecuciones.
                sorted_items = sorted(items_in_order, key=lambda x: x.get('Raw SKU', ''))
                for i, item in enumerate(sorted_items):
                    base_barcode = item.get('AssignedBaseBarcode')
                    suffix = f"{i + 1:02d}"  # Sufijo de dos dígitos: 01, 02, etc.
                    item['FinalBarcode'] = f"{base_barcode}{suffix}"
                    logger.debug(f"Pedido multi-ítem {order_id}: Asignado {item['FinalBarcode']} a SKU {item.get('Raw SKU')}")
        
        logger.info("Pasada 2 completada.")