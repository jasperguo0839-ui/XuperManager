# services/checkout_service.py

from datetime import datetime
from models.order import Order, OrderItem

class CheckoutService:
    def __init__(self, repo, pricing_service):
        self.repo = repo
        self.pricing = pricing_service

    def checkout(self, cart, products_map: dict, inventory: dict, membership_tier: str = "REGULAR"):
        # membership_tier can be "REGULAR", "SILVER", "GOLD", "VIP", etc.
        # We'll pass that into pricing to apply membership discounts.
        # Validate stock and product existence
        for it in cart.items:
            if it.sku not in products_map:
                raise ValueError(f"SKU not found: {it.sku}")
            if inventory.get(it.sku, 0) < it.qty:
                raise ValueError(f"Insufficient stock for {it.sku}")

        # Build order items with pricing
        order_items: list[OrderItem] = []
        total = 0.0

        for it in cart.items:
            product = products_map[it.sku]
            base_unit_price = product["price"]

            # This is the context passed to PricingService
            context = {
                "membership": membership_tier,
            }

            final_unit_price = self.pricing.price_item(
                sku=it.sku,
                product=product,
                qty=it.qty,
                base_unit_price=base_unit_price,
                context=context,
            )

            subtotal = round(final_unit_price * it.qty, 2)
            total += subtotal

            order_items.append(
                OrderItem(
                    sku=it.sku,
                    qty=it.qty,
                    unit_price=final_unit_price,
                    subtotal=subtotal,
                )
            )

        total = round(total, 2)

        # Deduct stock
        for it in cart.items:
            inventory[it.sku] -= it.qty

        # Persist order
        orders = self.repo.get_orders()
        order_id = f"ORD-{len(orders)+1:06d}"
        order = Order(
            order_id=order_id,
            created_at=datetime.now(),
            items=order_items,
            total=total,
        )

        orders.append({
            "order_id": order.order_id,
            "created_at": order.created_at.isoformat(),
            "items": [vars(x) for x in order.items],
            "total": order.total
        })

        self.repo.save_orders(orders)
        self.repo.save_inventory(inventory)

        # Clear cart
        cart.clear()

        return order