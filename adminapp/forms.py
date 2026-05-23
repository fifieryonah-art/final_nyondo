from django import forms
from .models import Supplier, SupplierPayment
from django.contrib.auth.models import User
from nyondoapp.models import Employee


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
    
   