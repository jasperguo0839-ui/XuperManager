# models/product.py
from dataclasses import dataclass
# Product model representing a product in the supermarket.
@dataclass
class Product:
    sku: str          
    name: str
    category: str
    price: float      
    active: bool = True