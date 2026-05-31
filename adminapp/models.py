from decimal import Decimal

from django.db import models


# Create your models here.
class Supplier(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    address = models.CharField(max_length=50)
    contact = models.CharField(max_length=15, blank=True)
    email = models.EmailField(unique=True)  
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outstanding_credit = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    amount_paid = models.DecimalField(max_digits=12,decimal_places=2,default=0)

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Partial", "Partial"),
        ("Paid", "Paid"),
    ]

    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="Pending")

    def __str__(self):
        return self.name
    
class SupplierPayment(models.Model):
    supplier = models.ForeignKey(Supplier,on_delete=models.CASCADE,related_name='payments')
    amount_paid = models.DecimalField(max_digits=10,decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    comment = models.TextField(blank=True,null=True)

    def __str__(self):
        return f"{self.supplier.name} - {self.amount_paid}"
    
class DepositScheme(models.Model):

    customer = models.ForeignKey('nyondoapp.Customer',on_delete=models.SET_NULL,null=True)
    product = models.ForeignKey('nyondoapp.Product',on_delete=models.SET_NULL,null=True)
    total_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    amount_paid = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    balance = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    quantity_expected = models.PositiveIntegerField()

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Active", "Active"),
        ("Completed", "Completed"),
        ("Withdrawn", "Withdrawn"),
        ("Cancelled", "Cancelled"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.product is not None and self.quantity_expected is not None:
            unit_price = self.product.unit_price or Decimal("0.00")
            self.total_amount = unit_price * Decimal(self.quantity_expected)
        self.balance = self.total_amount - self.amount_paid
        if self.status == "Cancelled" or self.status == "Withdrawn":
            pass
        elif self.amount_paid <= 0:
            self.status = "Pending"
        elif self.balance <= 0:
            self.status = "Completed"
        elif self.status != "Cancelled":
            self.status = "Active"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.name} - {self.product.name}"



class DepositPayment(models.Model):

    scheme = models.ForeignKey(DepositScheme, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)

    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Cash'),
            ('mtn', 'MTN Mobile Money'),
            ('airtel', 'Airtel Money'),
            ('bank', 'Bank Transfer'),
        ],
        default='cash'
    )

    comment = models.TextField(blank=True, null=True)
    received_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            import uuid
            self.receipt_number = f"DEP-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.scheme.customer.name} - {self.amount_paid} - {self.receipt_number}"


class DepositWithdrawal(models.Model):
    """Tracks when a customer withdraws goods from their deposit scheme"""

    scheme = models.ForeignKey(DepositScheme, on_delete=models.CASCADE, related_name='withdrawals')
    quantity_withdrawn = models.PositiveIntegerField()
    withdrawal_date = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)
    received_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    comment = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            import uuid
            self.receipt_number = f"WDR-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.scheme.customer.name} - Qty: {self.quantity_withdrawn} - {self.receipt_number}"
