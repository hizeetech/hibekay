# In your app's views.py
from django.contrib.auth import logout
from django.shortcuts import redirect

def custom_logout(request):
    logout(request)
    return redirect('admin:index')  # Redirect to the admin index page