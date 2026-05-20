from django import forms
from .models import Customer
from adminapp.models import Supplier



    
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = "__all__"



        

