"""
Core domain data models and structures
"""
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class OrderItem:
    """Represents an individual item from an order"""
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
    """Result of matching with the catalog"""
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
    """Result of order processing"""
    expedited_orders: List[OrderItem]
    standard_orders: List[OrderItem]
    unmatched_items: List[Dict]
    stats: Dict[str, int]