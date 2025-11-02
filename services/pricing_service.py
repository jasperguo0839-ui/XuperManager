# services/pricing_service.py

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, time
from typing import Dict, Any, List


class DiscountRule(ABC):
    #Abstract base class for all discount rules.
    #Each rule gets a chance to modify the unit price.

    @abstractmethod
    def apply(
        self,
        sku: str,
        product: Dict[str, Any],
        qty: int,
        unit_price: float,
        context: Dict[str, Any],
    ) -> float:
        pass


class CategoryDiscountRule(DiscountRule):
    # Example: discount certain categories (e.g. Dairy 10% off).
    # category_discounts is a dict like {"Dairy": 0.10, "Bakery": 0.05}
    # which means "10% off Dairy", "5% off Bakery".

    def __init__(self, category_discounts: Dict[str, float]):
        self.category_discounts = category_discounts

    def apply(self, sku, product, qty, unit_price, context):
        category = product.get("category", "")
        if category in self.category_discounts:
            rate = self.category_discounts[category]  # e.g. 0.10 = 10% off
            discounted = unit_price * (1.0 - rate)
            return round(discounted, 2)
        return unit_price


class TimeDiscountRule(DiscountRule):
    # Example: 'Happy Hour' pricing during a time window.
    # If current time is between start_time and end_time (inclusive),
    # apply a percentage discount.

    def __init__(self, start_time: time, end_time: time, rate: float):
        """
        rate: e.g. 0.05 for 5% off
        """
        self.start_time = start_time
        self.end_time = end_time
        self.rate = rate

    def apply(self, sku, product, qty, unit_price, context):
        # get "now" from context if provided for testability,
        # otherwise use real current time
        now: datetime = context.get("now", datetime.now())
        now_t = now.time()

        # assumes start_time <= end_time, basic case
        in_window = self.start_time <= now_t <= self.end_time

        if in_window:
            discounted = unit_price * (1.0 - self.rate)
            return round(discounted, 2)

        return unit_price


class MembershipDiscountRule(DiscountRule):
    """
    Apply extra discount based on membership tier.
    Example:
        tiers = {
            "REGULAR": 0.00,
            "SILVER": 0.02,  # 2% off
            "GOLD":   0.05,  # 5% off
            "VIP":    0.08   # 8% off
        }
    """

    def __init__(self, tier_discounts: Dict[str, float]):
        self.tier_discounts = tier_discounts

    def apply(self, sku, product, qty, unit_price, context):
        tier = context.get("membership", "REGULAR")
        if tier in self.tier_discounts:
            rate = self.tier_discounts[tier]
            discounted = unit_price * (1.0 - rate)
            return round(discounted, 2)
        return unit_price


class BulkQuantityRule(DiscountRule):
    #Optional: buy in bulk to get cheaper per-unit price.
    #Example: if qty >= threshold, apply rate.

    def __init__(self, threshold: int, rate: float):
        # threshold: e.g. 3 (buy 3 or more)
        # rate: e.g. 0.05 means 5% off per unit
        self.threshold = threshold
        self.rate = rate

    def apply(self, sku, product, qty, unit_price, context):
        if qty >= self.threshold:
            discounted = unit_price * (1.0 - self.rate)
            return round(discounted, 2)
        return unit_price


class PricingService:
    # The PricingService applies all registered discount rules in sequence.
    # Each rule receives the updated price so far, so discounts "stack".

    def __init__(self):
        self.rules: List[DiscountRule] = []

    def add_rule(self, rule: DiscountRule):
        self.rules.append(rule)

    def price_item(
        self,
        sku: str,
        product: Dict[str, Any],
        qty: int,
        base_unit_price: float,
        context: Dict[str, Any] | None = None,
    ) -> float:
        # Return the final unit price for one item after applying all rules.

        if context is None:
            context = {}

        price = base_unit_price

        for rule in self.rules:
            price = rule.apply(sku, product, qty, price, context)
            # safety clamp
            if price < 0:
                price = 0.0

        # final rounding to 2 decimal places
        return round(price, 2)