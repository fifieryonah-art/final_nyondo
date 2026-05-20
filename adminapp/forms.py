from django import forms
from .models import Supplier, SupplierPayment


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = "__all__"

class SupplierPaymentForm(forms.ModelForm):

    class Meta:

        model = SupplierPayment

        fields = [
            'amount_paid',
            'comment'
        ]