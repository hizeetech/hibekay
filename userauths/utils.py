# userauths/utils.py

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def check_role_customer(user):
    if user.is_authenticated and hasattr(user, 'profile'):
        return user.profile.user_type == "Customer"
    return False

def check_role_vendor(user):
    if user.is_authenticated and hasattr(user, 'profile'):
        return user.profile.user_type == "Vendor"
    return False

def redirect_by_user_type(user):
    if check_role_vendor(user):
        return 'vendor:dashboard'
    elif check_role_customer(user):
        return 'customer:dashboard'
    return 'store:index'

def customer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('userauths:sign-in')
        if not check_role_customer(request.user):
            return redirect(redirect_by_user_type(request.user))
        return view_func(request, *args, **kwargs)
    return wrapper

def vendor_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('userauths:sign-in')
        if not check_role_vendor(request.user):
            return redirect(redirect_by_user_type(request.user))
        return view_func(request, *args, **kwargs)
    return wrapper