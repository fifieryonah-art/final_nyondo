from django.db import models
from django.contrib.auth.models import User
from adminapp.models import Supplier


# Create your models here.
class Employee(models.Model):

    ROLE_CHOICES = [
        ('attendant', 'Sales Attendant'),
        ('manager', 'Store Manager'),
        ('admin', 'Accounts/Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    employee_id = models.CharField(max_length=50, unique=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    gender = models.CharField(max_length=20)

    def __str__(self):
        return self.user.username


class Product(models.Model):
    name = models.TextField()
    description = models.TextField()
    specification = models.TextField()
    stock_quantity = models.PositiveIntegerField(default=0)
    type = models.CharField(max_length=50, blank=True, null=True)
    cost_price = models.DecimalField(max_digits=50, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    profit_margin = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True) # foreign key means this feild creates a many to one relationship eg many products can belong to one supplier
    # SET_NULL means that when the related record is deleted, the connection is removed but the current record remains in the database.
    reorder_level = models.PositiveIntegerField(default=10)


    def save(self,  *args, **kwargs):
        self.profit_margin = self.unit_price - self.cost_price
        super().save(*args, **kwargs)


    def __str__(self):
        return self.name


class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_arrival = models.DateField(auto_now_add=True)
    time_arrival = models.TimeField(auto_now_add=True)
    comments = models.TextField()
    total_cost = models.DecimalField(max_digits=100, decimal_places=2)
    is_on_credit = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=True)

    def __str__(self):
        return self.product.name


class Customer(models.Model):
    name = models.CharField(max_length=100)
    on_scheme = models.BooleanField(default=False)
    phone = models.CharField(max_length=15)
    nin = models.TextField(unique=True)
    other_details = models.TextField()

    def __str__(self):
        return self.name

class Sale(models.Model):

    PAYMENT_METHODS =[
        ('cash', 'cash'),
        ('mtn', 'MTN Mobile Money'),
        ('airtel', 'Airtel Money'),
        ('card', 'Bank Card'),
    ]
    
    name = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    distance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2, editable=False)
    transport = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    sub_total = models.DecimalField(max_digits=20, decimal_places=2)
    customer_name = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    final_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS)
    comments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, unique=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.unit_price = self.name.unit_price
        self.sub_total = (self.quantity * self.unit_price)
        
        self.final_amount = (self.sub_total + self.transport)

        super().save(*args, **kwargs)



    def __str__(self):
        return f"Sale #(self.id)"


class Payment(models.Model):

    PAYMENT_METHODS =[
        ('cash', 'cash'),
        ('mtn', 'MTN Mobile Money'),
        ('airtel', 'Airtel Money'),
        ('card', 'Bank Card'),
    ]

    STATUS_CHOICES =[
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('pending', 'pending'),
    ]
    
    order_id = models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    total = models.DecimalField(max_digits=20, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS)
    receipt_number = models.CharField(max_length=50, unique=True)
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    distance = models.PositiveIntegerField(default=0)
    

    def __str__(self):
        return self.receipt_number
    



