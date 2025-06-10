"""
Modelos de datos y estructuras centrales del dominio
"""
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class OrderItem:
    """Representa un item individual de una orden"""
    order_id: str
    item_number: str
    transaction_id: str
    store_id: str
    sku: str
    title: str
    quantity: int
    template_match: Optional['TemplateMatch'] = None
    barcode: Optional[str] = None
    
@dataclass
class TemplateMatch:
    """Resultado de matching con el catálogo"""
    template: str
    company: str
    model: str
    year: str
    mats: str
    clips: str
    clip_type: str
    confidence_score: float = 0.0
    match_method: str = ""

@dataclass
class ProcessingResult:
    """Resultado del procesamiento de órdenes"""
    expedited_orders: List[OrderItem]
    standard_orders: List[OrderItem]
    unmatched_items: List[Dict]
    stats: Dict[str, int]