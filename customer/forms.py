# customer/forms.py
from django import forms
from customer.models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'full_name', 
            'mobile',
            'email',
            'country',
            'state',
            'city',
            'address',
            'zip_code'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any custom form initialization here