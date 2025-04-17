# userauths/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox # type: ignore

from userauths.models import User

USER_TYPE = (
    ("Vendor", "Vendor"),
    ("Customer", "Customer"),
)

class UserRegisterForm(UserCreationForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder':'Full Name'}), required=True)
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder':'Mobile Number'}), required=True)
    email = forms.EmailField(widget=forms.TextInput(attrs={'class': 'form-control rounded' , 'placeholder':'Email Address'}), required=True)
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control rounded' , 'placeholder':'Password'}), required=True)
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={ 'class': 'form-control rounded' , 'placeholder':'Confirm Password'}), required=True)
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())
    vendor_license = forms.FileField(required=False, help_text='Please upload your business license or permit (PDF/Image)')
    user_type = forms.ChoiceField(choices=USER_TYPE, widget=forms.Select(attrs={"class": "form-select"}))

    class Meta:
        model = User
        fields = ['full_name', 'mobile', 'email', 'password1', 'password2', 'captcha', 'user_type', 'vendor_license']
        
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        user_type = cleaned_data.get("user_type")
        vendor_license = cleaned_data.get("vendor_license")

        if password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        if user_type == "Vendor" and not vendor_license:
            raise forms.ValidationError("Vendor license is required for vendor registration.")

        return cleaned_data
    
    
    
    def clean_vendor_license(self):
        vendor_license = self.cleaned_data.get('vendor_license')
        user_type = self.cleaned_data.get('user_type')
        
        if user_type == 'Vendor' and not vendor_license:
            raise forms.ValidationError("Vendor license is required for vendor accounts.")
        
        return vendor_license

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['email'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1']
        )
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs={'class': 'form-control rounded' , 'name': "email", 'placeholder':'Email Address'}), required=False)
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control rounded' , 'name': "password", 'placeholder':'Password'}), required=False)
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    class Meta:
        model = User
        fields = ['email', 'password', 'captcha']
