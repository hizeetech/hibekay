# userauths/views.py
from django.db import transaction
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.core.mail import send_mail
from django.conf import settings

from userauths import models as userauths_models
from userauths import forms as userauths_forms
from vendor import models as vendor_models
from .utils import check_role_customer, check_role_vendor, redirect_by_user_type, customer_required, vendor_required

logger = logging.getLogger(__name__)

def register_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in")
        return redirect(redirect_by_user_type(request.user))

    form = userauths_forms.UserRegisterForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                full_name = form.cleaned_data.get('full_name')
                email = form.cleaned_data.get('email')
                mobile = form.cleaned_data.get('mobile')
                password = form.cleaned_data.get('password1')
                user_type = form.cleaned_data.get("user_type")
                vendor_license = form.cleaned_data.get("vendor_license")

                # Use get_or_create to handle existing profiles
                profile, created = userauths_models.Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        'full_name': full_name,
                        'mobile': mobile,
                        'user_type': user_type,
                        'vendor_license': vendor_license if user_type == "Vendor" else None
                    }
                )

                # If profile already existed, update it
                if not created:
                    profile.full_name = full_name
                    profile.mobile = mobile
                    profile.user_type = user_type
                    if user_type == "Vendor":
                        profile.vendor_license = vendor_license
                    profile.save()

                if user_type == "Vendor":
                    vendor, vendor_created = vendor_models.Vendor.objects.get_or_create(
                        user=user,
                        defaults={
                            'store_name': full_name,
                            'is_approved': False
                        }
                    )

                    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
                    
                    # Send admin notification
                    try:
                        admin_subject = f"New Vendor Approval Request: {full_name}"
                        admin_message = f"""
                        A new vendor {full_name} has registered and is awaiting approval.
                        Email: {email}
                        Mobile: {mobile}
                        License: {vendor_license}
                        
                        Review: {site_url}/admin/vendor/vendor/{vendor.id}/change/
                        """
                        send_mail(
                            admin_subject,
                            admin_message,
                            settings.DEFAULT_FROM_EMAIL,
                            [settings.ADMIN_EMAIL],
                            fail_silently=False,
                        )
                    except Exception as e:
                        logger.error(f"Failed to send admin email: {str(e)}")

                    # Send vendor notification
                    try:
                        vendor_subject = "Vendor Account Pending Approval"
                        vendor_message = f"""
                        Dear {full_name},
                        Thank you for registering as a vendor. 
                        Your account is pending admin approval.
                        We'll notify you once approved.
                        """
                        send_mail(
                            vendor_subject,
                            vendor_message,
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                        )
                    except Exception as e:
                        logger.error(f"Failed to send vendor email: {str(e)}")

                    messages.info(request, "Vendor account pending admin approval.")
                    return redirect('userauths:sign-in')
                
                # For regular users
                user = authenticate(email=email, password=password)
                if user:
                    login(request, user)
                    messages.success(request, "Account created successfully!")
                    return redirect(redirect_by_user_type(user))
                else:
                    messages.error(request, "Failed to authenticate user")
                    return redirect('userauths:sign-up')

        except IntegrityError as e:
            logger.error(f"IntegrityError during registration: {str(e)}")
            messages.error(request, "Registration error. Please try again or contact support.")
            return redirect('userauths:sign-up')
            
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            messages.error(request, "An unexpected error occurred. Please try again.")
            return redirect('userauths:sign-up')

    context = {'form': form}
    return render(request, 'userauths/sign-up.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_by_user_type(request.user))
    
    if request.method == 'POST':
        form = userauths_forms.LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                # Vendor approval check
                if hasattr(user, 'vendor'):
                    if not user.vendor.is_approved:
                        messages.warning(request, "Vendor account pending approval.")
                        return redirect('userauths:sign-in')
                    if not user.vendor.is_active:
                        messages.error(request, "Vendor account deactivated.")
                        return redirect('userauths:sign-in')
                
                login(request, user)
                messages.success(request, "Login successful!")
                return redirect(redirect_by_user_type(user))
            else:
                messages.error(request, 'Invalid credentials')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return render(request, "userauths/sign-in.html", {'form': userauths_forms.LoginForm()})

def logout_view(request):
    cart_id = request.session.get('cart_id')
    logout(request)
    if cart_id:
        request.session['cart_id'] = cart_id
    messages.success(request, 'Logged out successfully.')
    return redirect("userauths:sign-in")

@vendor_required
def vendor_dashboard(request):
    if not request.user.vendor.is_approved:
        messages.warning(request, "Vendor account pending approval")
        return redirect('userauths:sign-in')
    return render(request, 'vendor/dashboard.html')

@customer_required
def customer_dashboard(request):
    return render(request, 'customer/dashboard.html')

def handler404(request, exception, *args, **kwargs):
    return render(request, 'userauths/404.html', status=404)

def handler500(request, *args, **kwargs):
    return render(request, 'userauths/500.html', status=500)