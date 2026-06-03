import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Supplier, SupplierPayment
from django.contrib.auth.models import User
from nyondoapp.models import Employee


UGANDAN_PHONE_REGEX = re.compile(r"^07\d{8}$")


def normalize_ugandan_phone(value):
    phone = (value or "").strip().replace(" ", "").replace("-", "")

    if phone.startswith("+"):
        phone = phone[1:]

    if phone.startswith("256"):
        phone = "0" + phone[3:]

    return phone


def validate_ugandan_phone(value):
    normalized_phone = normalize_ugandan_phone(value)

    if not normalized_phone:
        raise ValidationError("Phone number is required.")

    if not UGANDAN_PHONE_REGEX.fullmatch(normalized_phone):
        raise ValidationError(
            "Enter a valid Ugandan mobile number, for example 0770123456 or +256770123456."
        )

    return normalized_phone


class SupplierForm(forms.ModelForm):
    contact = forms.CharField(
        required=False,
        label="Phone Number",
        widget=forms.TextInput(attrs={"placeholder": "0770123456"}),
    )

    class Meta:
        model = Supplier
        fields = "__all__"

    def clean_contact(self):
        return validate_ugandan_phone(self.cleaned_data.get("contact"))

    def clean_outstanding_credit(self):
        value = self.cleaned_data.get('outstanding_credit')
        if value is not None and value < 0:
            raise ValidationError("Outstanding credit cannot be a negative value.")
        return value

    def clean_total_amount(self):
        value = self.cleaned_data.get('total_amount')
        if value is not None and value < 0:
            raise ValidationError("Total amount cannot be a negative value.")
        return value

    def clean_amount_paid(self):
        value = self.cleaned_data.get('amount_paid')
        if value is not None and value < 0:
            raise ValidationError("Amount paid cannot be a negative value.")
        return value


class SupplierPaymentForm(forms.ModelForm):

    class Meta:

        model = SupplierPayment

        fields = [
            'amount_paid',
            'comment'
        ]

class EmployeeCreationForm(forms.ModelForm):

    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Employee
        fields = ["employee_id", "role", "gender"]

    # validation
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

    def save(self, commit=True):
        username = self.cleaned_data["username"]
        email = self.cleaned_data.get("email")
        password = self.cleaned_data["password"]

        # create Django user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # create employee
        employee = super().save(commit=False)
        employee.user = user

        if commit:
            employee.save()

        return employee
    
   