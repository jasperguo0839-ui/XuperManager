# models/cart.py
from dataclasses import dataclass
# Cart model representing a shopping cart.
@dataclass
class CartItem:
    sku: str
    qty: int

class Cart:
    def __init__(self):
        self.items: list[CartItem] = []

    def add(self, sku: str, qty: int = 1):
        if qty <= 0: 
            raise ValueError("The quantity must be a positive number.")
        self.items.append(CartItem(sku, qty))

    def clear(self):
        self.items.clear()