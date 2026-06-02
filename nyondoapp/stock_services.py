"""Centralized stock service helpers.

Keep all stock mutations in one place to allow auditing, validation
and future hooks (notifications, logging, history models).
"""
import logging
from django.db import transaction

logger = logging.getLogger(__name__)


def update_stock(product, quantity_change, *, user=None, reason=None):
    """Update a product's stock quantity safely.

    Args:
        product: Product instance
        quantity_change: int - positive to increase, negative to decrease
        user: optional User who triggered the change
        reason: optional string describing why the change happened

    Raises:
        ValueError if resulting stock would be negative or input invalid.
    """
    try:
        qty_delta = int(quantity_change)
    except (TypeError, ValueError):
        raise ValueError("quantity_change must be an integer")

    if qty_delta == 0:
        # nothing to do
        return

    with transaction.atomic():
        new_qty = product.stock_quantity + qty_delta
        if new_qty < 0:
            raise ValueError(f"Insufficient stock for {product.name}. Requested change {qty_delta}, available {product.stock_quantity}.")

        product.stock_quantity = new_qty
        product.save(update_fields=["stock_quantity"])

        # Log change for audit readiness (can be replaced with a StockMovement model later)
        logger.info(
            "Stock update: product=%s delta=%s new=%s user=%s reason=%s",
            getattr(product, 'id', None), qty_delta, new_qty, getattr(user, 'id', None), reason,
        )