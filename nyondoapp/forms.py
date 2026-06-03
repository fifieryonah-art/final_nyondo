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
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0770123456 or +256770123456'})
    )

    class Meta:
        model = Customer
        exclude = ("id",)
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name'}),
            'nin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIN'}),
            'other_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional details'}),
            'on_scheme': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("Customer name is required.")
        return name

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            raise ValidationError("Phone number is required.")
        normalized = phone.replace(" ", "").replace("-", "")
        if normalized.startswith("+"):
            normalized = normalized[1:]
        if normalized.startswith("256"):
            normalized = "0" + normalized[3:]
        if not UGANDAN_PHONE_REGEX.fullmatch(normalized):
            raise ValidationError("Enter a valid Ugandan number e.g. 0770123456 or +256770123456.")
        return normalized

    def clean_nin(self):
        nin = (self.cleaned_data.get("nin") or "").strip()
        if not nin:
            raise ValidationError("NIN is required.")
        if not UGANDAN_NIN_REGEX.fullmatch(nin):
            raise ValidationError("Enter a valid 14-character alphanumeric NIN.")
        return nin


class ProductForm(forms.ModelForm):
    cost_price = forms.DecimalField(
        max_digits=50, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'})
    )
    unit_price = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'})
    )
    stock_quantity = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'specification', 'type', 'cost_price', 'unit_price', 'stock_quantity', 'reorder_level']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Product Description'}),
            'specification': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Technical Specifications'}),
            'type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Hardware, Tool'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("Product name is required.")
        return name

    def clean_cost_price(self):
        price = self.cleaned_data.get('cost_price')
        if price is None:
            raise ValidationError("Cost price is required.")
        if price < 0:
            raise ValidationError("Cost price cannot be negative.")
        return price

    def clean_unit_price(self):
        price = self.cleaned_data.get('unit_price')
        if price is None:
            raise ValidationError("Unit price is required.")
        if price <= 0:
            raise ValidationError("Unit price must be greater than 0.")
        return price

    def clean_stock_quantity(self):
        qty = self.cleaned_data.get('stock_quantity')
        if qty is None:
            raise ValidationError("Stock quantity is required.")
        if qty < 0:
            raise ValidationError("Stock quantity cannot be negative.")
        return qty

    def clean(self):
        cleaned_data = super().clean()
        unit_price = cleaned_data.get('unit_price')
        cost_price = cleaned_data.get('cost_price')
        if unit_price and cost_price and unit_price < cost_price:
            raise ValidationError("Unit price must be greater than or equal to cost price.")
        return cleaned_data


class ExpenseForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=20, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'})
    )

    class Meta:
        model = Expense
        fields = ['date', 'category', 'description', 'amount', 'payment_method', 'vendor', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the expense'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'vendor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vendor name'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes (optional)'}),
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
        if amount is None:
            raise ValidationError("Amount is required.")
        if amount <= 0:
            raise ValidationError("Amount must be greater than 0.")
        return amount

    def clean_description(self):
        desc = self.cleaned_data.get('description', '').strip()
        if not desc:
            raise ValidationError("Description is required.")
        if len(desc) < 5:
            raise ValidationError("Description must be at least 5 characters.")
        return desc

    def clean_category(self):
        cat = self.cleaned_data.get('category')
        if not cat:
            raise ValidationError("Category is required.")
        return cat

    def clean_payment_method(self):
        method = self.cleaned_data.get('payment_method')
        if not method:
            raise ValidationError("Payment method is required.")
        return method


class StockForm(forms.ModelForm):
    quantity = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    total_cost = forms.DecimalField(
        max_digits=100, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    class Meta:
        model = Stock
        fields = ['product', 'supplier', 'quantity', 'total_cost', 'comments', 'is_on_credit', 'is_paid']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_on_credit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is None:
            raise ValidationError("Quantity is required.")
        if qty <= 0:
            raise ValidationError("Quantity must be at least 1.")
        return qty

    def clean_total_cost(self):
        cost = self.cleaned_data.get('total_cost')
        if cost is None:
            raise ValidationError("Total cost is required.")
        if cost < 0:
            raise ValidationError("Total cost cannot be negative.")
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
