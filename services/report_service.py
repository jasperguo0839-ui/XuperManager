# services/report_service.py
from collections import Counter
from datetime import datetime
# report_service.py is a service module (Service Layer)
# with the class name ReportService, responsible for generating sales reports and inventory alerts.
class ReportService:
    def __init__(self, repo):
        self.repo = repo

    def sales_summary(self, start: str | None = None, end: str | None = None) -> dict:
        #This method returns a sales statistics report.
        #Parameters:
        #start: Start date (ISO date string, e.g., “2025-11-01T00:00:00”)
        # end: End date (same format)
        # If omitted, all orders are included in the statistics.
        orders = self.repo.get_orders()
        if start or end:
            def in_range(o):
                dt = datetime.fromisoformat(o["created_at"])
                return (start is None or dt >= datetime.fromisoformat(start)) and \
                       (end   is None or dt <= datetime.fromisoformat(end))
            orders = list(filter(in_range, orders))
        # Use Counter to track how many units of each product have been sold;
        # most_common(5) retrieves the top 5 best-selling items.
        revenue = sum(o["total"] for o in orders)
        counter = Counter()
        for o in orders:
            for it in o["items"]:
                counter[it["sku"]] += it["qty"]
        top5 = counter.most_common(5)
        return {"revenue": round(revenue, 2), "top5": top5}

    def low_stock(self, inventory: dict, threshold: int = 5) -> list[tuple[str,int]]:
        # Alert for products with low stock.
        return [(sku, qty) for sku, qty in inventory.items() if qty <= threshold]