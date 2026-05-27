#service file for auto reduction and auto add
def update_stock(product, quantity_change):
    """
    Central stock controller
    + quantity_change = increase stock
    - quantity_change = decrease stock
    """

    product.stock_quantity += quantity_change
    product.save(update_fields=["stock_quantity"])