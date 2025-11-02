# data/repository.py
import json
from pathlib import Path

class DataRepository:
    def __init__(self):
        # base folder where all JSON data lives
        self.storage_dir = Path("data/storage")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, filename: str) -> Path:
        return self.storage_dir / filename

    def _read_json(self, filename: str):
        # Load JSON from disk. If file does not exist or is empty/bad,
        # return a sensible default (usually [] or {} depending on caller).
        
        path = self._file_path(filename)
        if not path.exists():
            # file missing -> return empty
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()
                if text == "":
                    return []
                return json.loads(text)
        except Exception:
            # corrupted or unreadable -> fail safe
            return []

    def _write_json(self, filename: str, data) -> None:
        #Save Python data structure back to JSON file with pretty formatting.
        path = self._file_path(filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_products(self) -> list[dict]:
        data = self._read_json("products.json")
        if isinstance(data, list):
            return data
        # if corrupted format, recover gracefully
        return []

    def save_products(self, products: list[dict]) -> None:
        self._write_json("products.json", products)

    def get_inventory(self) -> dict[str, int]:
        #Returns {sku: quantity, ...}.
        #If file missing or bad, return {} (not []).
        data = self._read_json("inventory.json")
        if isinstance(data, dict):
            return data
        # first run or invalid -> treat as empty inventory
        return {}

    def save_inventory(self, inventory: dict[str, int]) -> None:
        self._write_json("inventory.json", inventory)


    def get_orders(self) -> list[dict]:
        # Returns a list of orders.
        data = self._read_json("orders.json")
        if isinstance(data, list):
            return data
        return []

    def save_orders(self, orders: list[dict]) -> None:
        self._write_json("orders.json", orders)

    def get_customers(self) -> list[dict]:
        # Returns a list of customers.
        data = self._read_json("customers.json")
        if isinstance(data, list):
            return data
        return []

    def save_customers(self, customers: list[dict]) -> None:
        self._write_json("customers.json", customers)


    def get_promotions(self) -> dict:
        # Returns promotions configuration.
        # If file missing or bad, return default structure.
        data = self._read_json("promotions.json")
        if not isinstance(data, dict):
            data = {}

        return {
            "category_discounts": data.get("category_discounts", {}),
            "happy_hour": data.get("happy_hour", {
                "start": "17:00",
                "end": "18:00",
                "rate": 0.05
            }),
            "bulk": data.get("bulk", {
                "threshold": 3,
                "rate": 0.05
            })
        }

    def save_promotions(self, promo: dict) -> None:
        self._write_json("promotions.json", promo)