# models/order.py
from dataclasses import dataclass
from datetime import datetime
# Order model representing a customer order.
@dataclass
class OrderItem:
    sku: str
    qty: int
    unit_price: float
    subtotal: float

@dataclass
class Order:
    order_id: str
    created_at: datetime
    items: list[OrderItem]
    total: float