# store/forms.py
from django import forms
from store.models import Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['title', 'image', 'slug']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter category name'
        })
        self.fields['slug'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'auto-generated if empty'
        })
        self.fields['image'].widget.attrs.update({
            'class': 'form-control'
        })