# services/membership_service.py
"""
membership_service.py

Provides helper functions for managing supermarket membership tiers.

Features:
- Automatically compute membership tier based on lifetime spending.
- Search for existing customers in the repository.
- Designed to work with customers.json data.

Example thresholds:
    REGULAR : spend < 100
    SILVER  : 100 ≤ spend < 500
    GOLD    : 500 ≤ spend < 1000
    VIP     : spend ≥ 1000
"""

from typing import List, Dict, Optional


def compute_tier(lifetime_spend: float) -> str:
    # Compute membership tier based on lifetime spending.
    if lifetime_spend >= 1000:
        return "VIP"
    elif lifetime_spend >= 500:
        return "GOLD"
    elif lifetime_spend >= 100:
        return "SILVER"
    else:
        return "REGULAR"


def find_customer(customers: List[Dict], customer_id: str) -> Optional[Dict]:
    # Search for a customer by customer_id in the customers list.
    for c in customers:
        if c["customer_id"] == customer_id:
            return c
    return None