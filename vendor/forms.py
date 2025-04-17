# vendor/forms.py

from django import forms
from store.models import Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["title", "image"]
