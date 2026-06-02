import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Customer, Expense, Product, Stock, Sale, Payment
from adminapp.models import Supplier


UGANDAN_PHONE_REGEX = re.compile(r"^07\d{8}$")
UGANDAN_NIN_REGEX = re.compile(r"^[A-Za-z0-9]{14}$")


class CustomerForm(forms.ModelForm):
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0770123456 or +256770123456',
            'data-validate': 'phone'
        })
    )
    
    class Meta:
        model = Customer
        exclude = ("id",)
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name'}),
            'nin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIN', 'data-validate': 'nin'}),
            'other_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional details'}),
            'on_scheme': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()

        if not phone:
            raise ValidationError("Phone number is required.")

        normalized_phone = phone.replace(" ", "").replace("-", "")

        if normalized_phone.startswith("+"):
            normalized_phone = normalized_phone[1:]

        if normalized_phone.startswith("256"):
            normalized_phone = "0" + normalized_phone[3:]

        if not UGANDAN_PHONE_REGEX.fullmatch(normalized_phone):
            raise ValidationError(
                "Enter a valid Ugandan mobile number, for example 0770123456 or +256770123456."
            )

        return normalized_phone

    def clean_nin(self):
        nin = (self.cleaned_data.get("nin") or "").strip()

        if not nin:
            raise ValidationError("NIN is required.")

        if not UGANDAN_NIN_REGEX.fullmatch(nin):
            raise ValidationError("Enter a valid 14-character alphanumeric NIN.")

        return nin

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("Customer name is required.")
        return name


class ExpenseForm(forms.ModelForm):
    """Form for recording business expenses"""

    amount = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0.01',
            'data-validate': 'price'
        })
    )

    class Meta:
        model = Expense
        fields = ['date', 'category', 'description', 'amount', 'payment_method', 'vendor', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': 'required'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the expense',
                'required': 'required'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required'
            }),
            'vendor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Vendor or service provider name'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)'
            }),
        }

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if not date:
            raise ValidationError("Date is required.")
        if date > timezone.now().date():
            raise ValidationError("Date cannot be in the future.")
        return date

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if not amount or amount <= 0:
            raise ValidationError("Amount must be greater than 0.")
        return amount

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if not description:
            raise ValidationError("Description is required.")
        if len(description) < 5:
            raise ValidationError("Description must be at least 5 characters long.")
        return description

    def clean_category(self):
        category = self.cleaned_data.get('category')
        if not category:
            raise ValidationError("Category is required.")
        return category

    def clean(self):
        cleaned_data = super().clean()
        # Ensure all required fields are filled
        required_fields = ['date', 'category', 'description', 'amount', 'payment_method']
        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, "This field is required.")
        return cleaned_data


class ProductForm(forms.ModelForm):
    """Form for managing products with validation"""

    cost_price = forms.DecimalField(
        max_digits=50,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'data-validate': 'price'
        })
    )

    unit_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'data-validate': 'price'
        })
    )

    stock_quantity = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'data-validate': 'quantity',
            'min': '0'
        })
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'specification', 'type', 'cost_price', 'unit_price', 'stock_quantity', 'reorder_level']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name', 'required': 'required'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Product Description'}),
            'specification': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Technical Specifications'}),
            'type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Type (e.g., Hardware, Tool)'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'data-validate': 'quantity', 'min': '0'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("Product name is required.")
        return name

    def clean_cost_price(self):
        price = self.cleaned_data.get('cost_price')
        if not price or price < 0:
            raise ValidationError("Cost price must be a positive number.")
        return price

    def clean_unit_price(self):
        price = self.cleaned_data.get('unit_price')
        if not price or price <= 0:
            raise ValidationError("Unit price must be greater than 0.")
        return price

    def clean(self):
        cleaned_data = super().clean()
        unit_price = cleaned_data.get('unit_price')
        cost_price = cleaned_data.get('cost_price')
        if unit_price and cost_price and unit_price < cost_price:
            raise ValidationError("Unit price must be greater than or equal to cost price.")
        return cleaned_data


class StockForm(forms.ModelForm):
    """Form for managing stock with validation"""

    quantity = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'data-validate': 'quantity',
            'min': '1'
        })
    )

    total_cost = forms.DecimalField(
        max_digits=100,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'data-validate': 'price',
            'step': '0.01'
        })
    )

    class Meta:
        model = Stock
        fields = ['product', 'supplier', 'quantity', 'total_cost', 'comments', 'is_on_credit', 'is_paid']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control', 'required': 'required'}),
            'supplier': forms.Select(attrs={'class': 'form-control', 'required': 'required'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any additional comments'}),
            'is_on_credit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if not quantity or quantity <= 0:
            raise ValidationError("Quantity must be at least 1.")
        return quantity

    def clean_total_cost(self):
        cost = self.cleaned_data.get('total_cost')
        if not cost or cost < 0:
            raise ValidationError("Total cost must be a positive number.")
        return cost

    def clean_product(self):
        product = self.cleaned_data.get('product')
        if not product:
            raise ValidationError("Product is required.")
        return product

    def clean_supplier(self):
        supplier = self.cleaned_data.get('supplier')
        if not supplier:
            raise ValidationError("Supplier is required.")
        return supplier

