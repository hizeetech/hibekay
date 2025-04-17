# customer/views.py
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.urls import reverse

from plugin.paginate_queryset import paginate_queryset
from store import models as store_models
from customer import models as customer_models

from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash  # Add this

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from customer.forms import AddressForm  # You'll need to create this form
from userauths.utils import customer_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from . import models as customer_models



@login_required
@customer_required
def dashboard(request):
    orders_list = store_models.Order.objects.filter(customer=request.user)
    orders = paginate_queryset(request, orders_list, 5)
    total_spent = store_models.Order.objects.filter(customer=request.user).aggregate(total = models.Sum("total"))['total']
    notis = customer_models.Notifications.objects.filter(user=request.user, seen=False)

    context = {
        "orders": orders,
        "orders_list": orders_list,  # For pagination links
        "total_spent": total_spent,
        "notis": notis,
    }

    return render(request, "customer/dashboard.html", context)


@login_required
def orders(request):
    orders_list = store_models.Order.objects.filter(customer=request.user)
    orders = paginate_queryset(request, orders_list, 3)

    context = {
        "orders": orders,
        "orders_list": orders_list,  # For pagination links
    }

    return render(request, "customer/orders.html", context)


@login_required
def order_detail(request, order_id):
    order = store_models.Order.objects.get(customer=request.user, order_id=order_id)

    context = {
        "order": order,
    }

    return render(request, "customer/order_detail.html", context)

@login_required
def order_item_detail(request, order_id, item_id):
    order = store_models.Order.objects.get(customer=request.user, order_id=order_id)
    item = store_models.OrderItem.objects.get(order=order, item_id=item_id)
    
    context = {
        "order": order,
        "item": item,
    }

    return render(request, "customer/order_item_detail.html", context)



def paginate_queryset(request, queryset, page_size):
    paginator = Paginator(queryset, page_size)
    page = request.GET.get('page')
    try:
        return paginator.get_page(page)
    except PageNotAnInteger:
        return paginator.get_page(1)
    except EmptyPage:
        return paginator.get_page(paginator.num_pages)


@login_required
def wishlist(request):
    wishlist_list = customer_models.Wishlist.objects.filter(user=request.user)
    wishlist = paginate_queryset(request, wishlist_list, 3)

    context = {
        "wishlist": wishlist,
        "wishlist_list": wishlist_list,
    }

    return render(request, "customer/wishlist.html", context)


@require_POST
@login_required
def remove_from_wishlist(request):
    wishlist_id = request.POST.get('wishlist_id')
    wishlist = get_object_or_404(customer_models.Wishlist, user=request.user, id=wishlist_id)
    wishlist.delete()
    count = customer_models.Wishlist.objects.filter(user=request.user).count()  # Get updated count
    return JsonResponse({'success': True, 'count': count})


@login_required
def wishlist_count(request):
    count = customer_models.Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({'count': count})


@require_POST
@login_required
def toggle_wishlist(request):
    product_id = request.POST.get('product_id')
    product = get_object_or_404(store_models.Product, id=product_id)

    wishlist_item = customer_models.Wishlist.objects.filter(
        user=request.user,
        product=product
    ).first()

    if wishlist_item:
        wishlist_item.delete()
        added = False
    else:
        customer_models.Wishlist.objects.create(user=request.user, product=product)
        added = True

    count = customer_models.Wishlist.objects.filter(user=request.user).count()  # Get updated count
    return JsonResponse({'added': added, 'count': count})


def add_to_wishlist(request, id):
    if request.user.is_authenticated:
        product = store_models.Product.objects.get(id=id)
        customer_models.Wishlist.objects.create(product=product, user=request.user)
        wishlist = customer_models.Wishlist.objects.filter(user=request.user)
        return JsonResponse({"message": "Item added to wishlist", "wishlist_count": wishlist.count()})
    else:
        return JsonResponse({"message": "User is not logged in", "wishlist_count": "0"})
    

@login_required
def notis(request):
    notis_list = customer_models.Notifications.objects.filter(user=request.user, seen=False)
    notis = paginate_queryset(request, notis_list, 10)

    context = {
        "notis": notis,
        "notis_list": notis_list,
    }
    return render(request, "customer/notis.html", context)

@login_required
def mark_noti_seen(request, id):
    noti = customer_models.Notifications.objects.get(user=request.user, id=id)
    noti.seen = True
    noti.save()

    messages.success(request, "Notification marked as seen")
    return redirect("customer:notis")


@login_required
def addresses(request):
    addresses_list = customer_models.Address.objects.filter(user=request.user)

    # Pagination
    paginator = Paginator(addresses_list, 3)  # Show 3 addresses per page
    page = request.GET.get('page')

    try:
        addresses = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        addresses = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        addresses = paginator.page(paginator.num_pages)

    context = {
        "addresses": addresses,
        "addresses_list": addresses_list,  # For pagination links
    }

    return render(request, "customer/addresses.html", context)

@login_required
def address_detail(request, id):
    address = customer_models.Address.objects.get(user=request.user, id=id)
    
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        mobile = request.POST.get("mobile")
        email = request.POST.get("email")
        country = request.POST.get("country")
        state = request.POST.get("state")
        city = request.POST.get("city")
        address_location = request.POST.get("address")
        zip_code = request.POST.get("zip_code")

        address.full_name = full_name
        address.mobile = mobile
        address.email = email
        address.country = country
        address.state = state
        address.city = city
        address.address = address_location
        address.zip_code = zip_code
        address.save()

        messages.success(request, "Address updated")
        return redirect("customer:address_detail", address.id)
    
    context = {
        "address": address,
    }

    return render(request, "customer/address_detail.html", context)



@login_required
def address_create(request):
    """
    Handles address creation with proper validation and redirect flow
    - Uses Django forms for validation
    - Better handling of redirects
    - Improved error messages
    - Sets first address as default automatically
    """
    
    # Set redirect URL if coming from cart
    set_redirect_url(request)
    
    if request.method == "POST":
        form = AddressForm(request.POST)
        
        if form.is_valid():
            address = save_address_from_form(request.user, form)
            handle_success_redirect(request, address)
            return redirect(get_success_url(request))
        
        # Form is invalid - show errors
        messages.error(request, "Please correct the errors below")
    else:
        form = AddressForm()
    
    return render(request, "customer/address_create.html", {'form': form})

def set_redirect_url(request):
    """Sets session redirect URL if coming from cart"""
    referer = request.META.get('HTTP_REFERER', '')
    if 'cart' in referer:
        request.session['next_url'] = reverse('store:cart')
        

def save_address_from_form(user, form):
    """Saves address from validated form data"""
    address = form.save(commit=False)
    address.user = user
    
    # Set as default if this is the user's first address
    if not customer_models.Address.objects.filter(user=user).exists():
        address.is_default = True
    
    address.save()
    return address

def handle_success_redirect(request, address):
    """Handles success messages and session cleanup"""
    messages.success(request, "Address created successfully")
    
    # If this was set as default, notify user
    if address.is_default:
        messages.info(request, "This address has been set as your default shipping address")

def get_success_url(request):
    """Determines where to redirect after successful creation"""
    next_url = request.session.pop('next_url', None)
    return next_url if next_url else 'customer:addresses'


# customer/views.py
@login_required
def set_default_address(request, id):
    address = get_object_or_404(customer_models.Address, id=id, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, "Default address set successfully")
    return redirect('customer:addresses')


@login_required
def delete_address(request, id):
    address = customer_models.Address.objects.get(user=request.user, id=id)
    address.delete()
    messages.success(request, "Address deleted")
    return redirect("customer:addresses")


@login_required
def profile(request):
    profile = request.user.profile

    if request.method == "POST":
        image = request.FILES.get("image")
        full_name = request.POST.get("full_name")
        mobile = request.POST.get("mobile")
    
        if image != None:
            profile.image = image

        profile.full_name = full_name
        profile.mobile = mobile

        request.user.save()
        profile.save()

        messages.success(request, "Profile Updated Successfully")
        return redirect("customer:profile")
    
    context = {
        'profile':profile,
    }
    return render(request, "customer/profile.html", context)

@login_required
def change_password(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_new_password = request.POST.get("confirm_new_password")

        # Add validation for password strength if needed
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters")
            return redirect("customer:change_password")

        if confirm_new_password != new_password:
            messages.error(request, "New passwords don't match")
            return redirect("customer:change_password")
        
        if check_password(old_password, request.user.password):
            request.user.set_password(new_password)
            request.user.save()
            
            # Important: Update session to prevent logout
            update_session_auth_hash(request, request.user)
            
            messages.success(request, "Password changed successfully!")
            return redirect("customer:profile")
        else:
            messages.error(request, "Current password is incorrect")
            return redirect("customer:change_password")
    
    return render(request, "customer/change_password.html")