# models/inventory.py
# Inventory model representing stock levels of products.
class Inventory:
    def __init__(self):
        self.stock: dict[str, int] = {}  # sku -> quantity

    def add_stock(self, sku: str, qty: int) -> None:
        if qty <= 0: 
            raise ValueError("New inventory must be a positive number.")
        self.stock[sku] = self.stock.get(sku, 0) + qty

    def reduce_stock(self, sku: str, qty: int) -> None:
        if self.stock.get(sku, 0) < qty:
            raise ValueError("Insufficient stock")
        self.stock[sku] -= qty