import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Customer
from adminapp.models import Supplier


UGANDAN_PHONE_REGEX = re.compile(r"^07\d{8}$")
UGANDAN_NIN_REGEX = re.compile(r"^[A-Za-z0-9\-]{5,30}$")


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        exclude = ("id",)

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
            raise ValidationError("Enter a valid alphanumeric NIN.")

        return nin
