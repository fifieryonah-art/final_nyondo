from django.db import models


# Create your models here.
class Supplier(models.Model):
    name = models.CharField(max_length=100)
    product = models.ForeignKey('nyondoapp.Product', on_delete=models.SET_NULL, null=True)
    category = models.CharField(max_length=50)
    address = models.CharField(max_length=50)
    contact = models.CharField(max_length=15, blank=True)
    email = models.EmailField(unique=True)  
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
        ("Active", "Active"),
        ("Completed", "Completed"),
          ("Cancelled", "Cancelled"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    payment_date = models.DateTimeField(auto_now_add=True)

def save(self, *args, **kwargs):
    # auto-calculate balance every time
    self.balance = self.total_amount - self.amount_paid
    super().save(*args, **kwargs)

def __str__(self):
    return f"{self.customer.name} - {self.product.name}"



class DepositPayment(models.Model):

    scheme = models.ForeignKey(DepositScheme,on_delete=models.CASCADE,related_name='payments')
    amount_paid = models.DecimalField(max_digits=12,decimal_places=2)

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

    comment = models.TextField(blank=True,null=True)
    received_by = models.ForeignKey('auth.User',on_delete=models.SET_NULL, null=True)

    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.scheme.customer.name}"
