# vendor/decorators.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages

def vendor_required(view_func):
    """
    Decorator that checks if the user is authenticated, is a vendor, and is approved.
    """
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'vendor'):
            messages.warning(request, "Vendor account required to access this page")
            return redirect('userauths:sign-in')
        if not request.user.vendor.is_approved:
            messages.warning(request, "Your vendor account is pending approval")
            return redirect('vendor:approval_pending')
        return view_func(request, *args, **kwargs)
    return _wrapped_view