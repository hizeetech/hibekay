# store/decorators.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages

def vendor_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or request.user.profile.user_type != "Vendor":
            messages.warning(request, "You need to be a vendor to access this page.")
            return redirect("userauths:sign-in")
        return view_func(request, *args, **kwargs)
    return _wrapped_view