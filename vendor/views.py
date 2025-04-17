# vendor/views.py
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.db.models.functions import TruncMonth
from django.db.models import Count
from functools import wraps
import json
from django.conf import settings

from plugin.paginate_queryset import paginate_queryset
from store import models as store_models
from userauths.utils import vendor_required
from vendor import models as vendor_models
from store.forms import CategoryForm

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .decorators import vendor_required
from .models import BankAccount, PayPalAccount, NIGERIAN_BANKS

# ============== Utility Functions ==============
def get_monthly_sales():
    monthly_sales = (
        store_models.OrderItem.objects
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(order_count=Count('id'))
        .order_by('month')
    )
    return monthly_sales

def approved_vendor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'vendor') or not request.user.vendor.is_approved:
            messages.warning(request, "Vendor approval required")
            return redirect('vendor:approval_pending')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ============== Core Vendor Views ==============
@login_required
def approval_pending(request):
    if not hasattr(request.user, 'vendor'):
        return redirect('store:index')
    
    if request.user.vendor.is_approved:
        return redirect('vendor:dashboard')
    
    if not request.session.get('pending_email_sent', False):
        request.user.vendor.send_pending_approval_notification()
        request.session['pending_email_sent'] = True
    
    return render(request, 'vendor/approval_pending.html')

@login_required
@vendor_required
def dashboard(request):
    if not request.user.vendor.is_approved:
        messages.warning(request, "Your vendor account is pending approval")
        return redirect('vendor:approval_pending')
    
    products = store_models.Product.objects.filter(vendor=request.user).order_by('-date')[:5]
    orders = store_models.Order.objects.filter(vendors=request.user, payment_status="Paid").order_by('-date')[:5]
    revenue = store_models.OrderItem.objects.filter(vendor=request.user).aggregate(total=models.Sum("total"))['total'] or 0
    notis = vendor_models.Notifications.objects.filter(user=request.user, seen=False)
    reviews = store_models.Review.objects.filter(product__vendor=request.user).order_by('-date')[:5]
    rating = store_models.Review.objects.filter(product__vendor=request.user).aggregate(avg=models.Avg("rating"))['avg'] or 0
    monthly_sales = get_monthly_sales()
    
    labels = [sale['month'].strftime('%B %Y') for sale in monthly_sales]
    data = [sale['order_count'] for sale in monthly_sales]
    categories = store_models.Category.objects.all()[:5]

    context = {
        "products": products,
        "orders": orders,
        "revenue": revenue,
        "notis": notis,
        "reviews": reviews,
        "rating": rating,
        "labels": json.dumps(labels),
        "data": json.dumps(data),
        "categories": categories,
    }
    return render(request, "vendor/dashboard.html", context)

# ============== Product Management ==============
@login_required
@approved_vendor_required
def products(request):
    products_list = store_models.Product.objects.filter(vendor=request.user)
    products = paginate_queryset(request, products_list, 10)

    context = {
        "products": products,
        "products_list": products_list,
    }
    return render(request, "vendor/products.html", context)

@login_required
@approved_vendor_required
def create_product(request):
    categories = store_models.Category.objects.all()

    if request.method == "POST":
        image = request.FILES.get("image")
        name = request.POST.get("name")
        category_id = request.POST.get("category_id")
        description = request.POST.get("description")
        price = request.POST.get("price")
        regular_price = request.POST.get("regular_price")
        shipping = request.POST.get("shipping")
        stock = request.POST.get("stock")

        product = store_models.Product.objects.create(
            vendor=request.user,
            image=image,
            name=name,
            category_id=category_id,
            description=description,
            price=price,
            regular_price=regular_price,
            shipping=shipping,
            stock=stock,
        )
        return redirect("vendor:update_product", product.id)
    
    context = {'categories': categories}
    return render(request, "vendor/create_product.html", context)

@login_required
@approved_vendor_required
def update_product(request, id):
    product = get_object_or_404(store_models.Product, id=id, vendor=request.user)
    categories = store_models.Category.objects.all()

    if request.method == "POST":
        product.name = request.POST.get("name")
        product.category_id = request.POST.get("category_id")
        product.description = request.POST.get("description")
        product.price = request.POST.get("price")
        product.regular_price = request.POST.get("regular_price")
        product.shipping = request.POST.get("shipping")
        product.stock = request.POST.get("stock")

        if image := request.FILES.get("image"):
            product.image = image
        product.save()

        # Handle variants and items
        variant_ids = request.POST.getlist('variant_id[]')
        variant_titles = request.POST.getlist('variant_title[]')

        if variant_ids and variant_titles:
            for i, variant_id in enumerate(variant_ids):
                variant_name = variant_titles[i]
                
                if variant_id:
                    variant = store_models.Variant.objects.filter(id=variant_id).first()
                    if variant:
                        variant.name = variant_name
                        variant.save()
                else:
                    variant = store_models.Variant.objects.create(product=product, name=variant_name)
                
                item_ids = request.POST.getlist(f'item_id_{i}[]')
                item_titles = request.POST.getlist(f'item_title_{i}[]')
                item_descriptions = request.POST.getlist(f'item_description_{i}[]')

                if item_ids and item_titles and item_descriptions:
                    for j in range(len(item_titles)):
                        item_id = item_ids[j]
                        item_title = item_titles[j]
                        item_description = item_descriptions[j]
                        
                        if item_id:
                            variant_item = store_models.VariantItem.objects.filter(id=item_id).first()
                            if variant_item:
                                variant_item.title = item_title
                                variant_item.content = item_description
                                variant_item.save()
                        else:
                            store_models.VariantItem.objects.create(
                                variant=variant,
                                title=item_title,
                                content=item_description
                            )

        for file_key, image_file in request.FILES.items():
            if file_key.startswith('image_'):
                store_models.Gallery.objects.create(product=product, image=image_file)

        messages.success(request, "Product updated successfully")
        return redirect("vendor:update_product", product.id)

    context = {
        'product': product,
        'categories': categories,
        'variants': store_models.Variant.objects.filter(product=product),
        'gallery_images': store_models.Gallery.objects.filter(product=product),
    }
    return render(request, "vendor/update_product.html", context)

@login_required
@approved_vendor_required
def delete_product(request, product_id):
    product = store_models.Product.objects.get(id=product_id, vendor=request.user)
    product.delete()
    messages.success(request, "Product deleted")
    return redirect("vendor:products")

# ============== Order Management ==============
@login_required
@approved_vendor_required
def orders(request):
    orders_list = store_models.Order.objects.filter(vendors=request.user, payment_status="Paid")
    orders = paginate_queryset(request, orders_list, 10)

    context = {
        "orders": orders,
        "orders_list": orders_list,
    }
    return render(request, "vendor/orders.html", context)

@login_required
@approved_vendor_required
def order_detail(request, order_id):
    order = store_models.Order.objects.get(vendors=request.user, order_id=order_id, payment_status="Paid")
    context = {"order": order}
    return render(request, "vendor/order_detail.html", context)

@login_required
@approved_vendor_required
def update_order_status(request, order_id):
    order = store_models.Order.objects.get(vendors=request.user, order_id=order_id, payment_status="Paid")
    
    if request.method == "POST":
        order.order_status = request.POST.get("order_status")
        order.save()
        messages.success(request, "Order status updated")
    
    return redirect("vendor:order_detail", order.order_id)

# ============== Profile & Settings ==============
@login_required
def profile(request):
    profile = request.user.profile

    if request.method == "POST":
        profile.full_name = request.POST.get("full_name")
        profile.mobile = request.POST.get("mobile")
        
        if image := request.FILES.get("image"):
            profile.image = image
        
        if hasattr(request.user, 'vendor'):
            vendor = request.user.vendor
            vendor.description = request.POST.get("description")
            vendor.country = request.POST.get("country")
            vendor.save()

        profile.save()
        messages.success(request, "Profile updated successfully")
        return redirect("vendor:profile")
    
    context = {
        'profile': profile,
        'vendor': getattr(request.user, 'vendor', None),
    }
    return render(request, "vendor/profile.html", context)

@login_required
@vendor_required
def settings(request):
    vendor = request.user.vendor
    bank_account, created = vendor_models.BankAccount.objects.get_or_create(vendor=vendor)
    
    if request.method == "POST":
        bank_account.account_type = request.POST.get("account_type")
        bank_account.bank_name = request.POST.get("bank_name")
        bank_account.account_number = request.POST.get("account_number")
        bank_account.account_name = request.POST.get("account_name")
        bank_account.save()
        messages.success(request, "Bank details updated successfully")
        return redirect('vendor:settings')
    
    context = {
        'bank_account': bank_account,
        'payout_methods': vendor_models.PAYOUT_METHOD,
    }
    return render(request, "vendor/settings.html", context)

# ============== Other Views ==============
@login_required
@approved_vendor_required
def coupons(request):
    coupons_list = store_models.Coupon.objects.filter(vendor=request.user)
    coupons = paginate_queryset(request, coupons_list, 10)

    context = {
        "coupons": coupons,
        "coupons_list": coupons_list,
    }
    return render(request, "vendor/coupons.html", context)

@login_required
@approved_vendor_required
def reviews(request):
    reviews_list = store_models.Review.objects.filter(product__vendor=request.user)
    rating = request.GET.get("rating")
    date = request.GET.get("date")

    if rating:
        reviews_list = reviews_list.filter(rating=rating)
    if date:
        reviews_list = reviews_list.order_by(date)

    reviews = paginate_queryset(request, reviews_list, 10)

    context = {
        "reviews": reviews,
        "reviews_list": reviews_list,
    }
    return render(request, "vendor/reviews.html", context)

# ============== Helper Views ==============
@login_required
def delete_variants(request, product_id, variant_id):
    product = store_models.Product.objects.get(id=product_id, vendor=request.user)
    variants = store_models.Variant.objects.get(product=product, id=variant_id)
    variants.delete()
    return JsonResponse({"message": "Variants deleted"})


@login_required
@approved_vendor_required
def delete_variants_items(request, variant_id, item_id):
    variant = get_object_or_404(store_models.Variant, id=variant_id, product__vendor=request.user)
    item = get_object_or_404(store_models.VariantItem, id=item_id, variant=variant)
    item.delete()
    return JsonResponse({"message": "Variant item deleted"})

@login_required
def delete_product_image(request, product_id, image_id):
    product = store_models.Product.objects.get(id=product_id, vendor=request.user)
    image = store_models.Gallery.objects.get(product=product, id=image_id)
    image.delete()
    return JsonResponse({"message": "Product Image deleted"})


from django.core.paginator import Paginator

# ============== Category Management ==============
@login_required
@approved_vendor_required
def categories(request):
    categories_list = store_models.Category.objects.filter(vendor=request.user)
    paginator = Paginator(categories_list, 10)
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)

    context = {
        "categories": categories,
        "categories_list": categories_list,
    }
    return render(request, "vendor/categories.html", context)

@login_required
@approved_vendor_required
def category_detail(request, id):
    category = get_object_or_404(store_models.Category, id=id, vendor=request.user)
    products = category.products.all()
    
    context = {
        "category": category,
        "products": products,
    }
    return render(request, "vendor/category_detail.html", context)

@login_required
@approved_vendor_required
def update_category(request, id):
    category = get_object_or_404(store_models.Category, id=id, vendor=request.user)
    
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully!")
            return redirect("vendor:category_detail", id=category.id)
    else:
        form = CategoryForm(instance=category)
    
    context = {
        "form": form,
        "category": category,
    }
    return render(request, "vendor/update_category.html", context)

@login_required
@approved_vendor_required
def delete_category(request, id):
    category = get_object_or_404(store_models.Category, id=id, vendor=request.user)
    
    if request.method == "POST":
        category.delete()
        messages.success(request, "Category deleted successfully!")
        return redirect("vendor:categories")
    
    context = {
        "category": category,
    }
    return render(request, "vendor/delete_category.html", context)

# ============== Order Item Management ==============
@login_required
@approved_vendor_required
def order_item_detail(request, order_id, item_id):
    order = store_models.Order.objects.get(vendors=request.user, order_id=order_id, payment_status="Paid")
    item = store_models.OrderItem.objects.get(item_id=item_id, order=order)
    
    context = {
        "order": order,
        "item": item,
    }
    return render(request, "vendor/order_item_detail.html", context)

@login_required
@approved_vendor_required
def update_order_item_status(request, order_id, item_id):
    order = store_models.Order.objects.get(vendors=request.user, order_id=order_id, payment_status="Paid")
    item = store_models.OrderItem.objects.get(item_id=item_id, order=order)
    
    if request.method == "POST":
        item.order_status = request.POST.get("order_status")
        item.shipping_service = request.POST.get("shipping_service")
        item.tracking_id = request.POST.get("tracking_id")
        item.save()

        messages.success(request, "Item status updated")
        return redirect("vendor:order_item_detail", order.order_id, item.item_id)
    
    return redirect("vendor:order_item_detail", order.order_id, item.item_id)

# ============== Notification Management ==============
@login_required
@vendor_required
def notis(request):
    notis_list = vendor_models.Notifications.objects.filter(user=request.user, seen=False)
    notis = paginate_queryset(request, notis_list, 10)

    context = {
        "notis": notis,
        "notis_list": notis_list,
    }
    return render(request, "vendor/notis.html", context)

@login_required
@vendor_required
def mark_noti_seen(request, id):
    noti = vendor_models.Notifications.objects.get(user=request.user, id=id)
    noti.seen = True
    noti.save()

    messages.success(request, "Notification marked as seen")
    return redirect("vendor:notis")

# ============== Password Management ==============
@login_required
def change_password(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_new_password = request.POST.get("confirm_new_password")

        if confirm_new_password != new_password:
            messages.error(request, "New passwords don't match")
            return redirect("vendor:change_password")
        
        if check_password(old_password, request.user.password):
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, "Password changed successfully")
            return redirect("vendor:profile")
        else:
            messages.error(request, "Old password is incorrect")
            return redirect("vendor:change_password")
    
    return render(request, "vendor/change_password.html")

# ============== Coupon Management ==============
@login_required
@approved_vendor_required
def update_coupon(request, id):
    coupon = store_models.Coupon.objects.get(vendor=request.user, id=id)
    
    if request.method == "POST":
        coupon.code = request.POST.get("coupon_code")
        coupon.save()
        messages.success(request, "Coupon updated")
    
    return redirect("vendor:coupons")

@login_required
@approved_vendor_required
def delete_coupon(request, id):
    coupon = store_models.Coupon.objects.get(vendor=request.user, id=id)
    coupon.delete()
    messages.success(request, "Coupon deleted")
    return redirect("vendor:coupons")

@login_required
@approved_vendor_required
def create_coupon(request):
    if request.method == "POST":
        code = request.POST.get("coupon_code")
        discount = request.POST.get("coupon_discount")
        store_models.Coupon.objects.create(vendor=request.user, code=code, discount=discount)
        messages.success(request, "Coupon created")
    
    return redirect("vendor:coupons")

# ============== Review Management ==============
@login_required
@approved_vendor_required
def update_reply(request, id):
    review = store_models.Review.objects.get(id=id)
    
    if request.method == "POST":
        review.reply = request.POST.get("reply")
        review.save()
        messages.success(request, "Reply added")
    
    return redirect("vendor:reviews")


# vendor/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .decorators import vendor_required
from .models import BankAccount, PayPalAccount, NIGERIAN_BANKS

@login_required
@vendor_required
def payout_settings(request):
    bank_account = None
    paypal_account = None
    
    try:
        bank_account = BankAccount.objects.get(vendor=request.user.vendor)
    except BankAccount.DoesNotExist:
        try:
            paypal_account = PayPalAccount.objects.get(vendor=request.user.vendor)
        except PayPalAccount.DoesNotExist:
            pass
    
    context = {
        'bank_account': bank_account,
        'paypal_account': paypal_account,
        'nigerian_banks': NIGERIAN_BANKS,
    }
    return render(request, 'vendor/settings.html', context)

@login_required
@vendor_required
def save_payout_settings(request):
    if request.method == 'POST':
        payout_method = request.POST.get('payout_method')
        
        if payout_method == 'nigerian_bank':
            # Delete any existing PayPal account
            PayPalAccount.objects.filter(vendor=request.user.vendor).delete()
            
            # Create or update bank account
            bank_account, created = BankAccount.objects.update_or_create(
                vendor=request.user.vendor,
                defaults={
                    'account_name': request.POST.get('account_name'),
                    'account_number': request.POST.get('account_number'),
                    'bank_name': request.POST.get('bank_name'),
                    'is_updated': True,
                }
            )
            messages.success(request, 'Bank account details updated successfully!')
        else:
            # Delete any existing bank account
            BankAccount.objects.filter(vendor=request.user.vendor).delete()
            
            # Create or update PayPal account
            paypal_account, created = PayPalAccount.objects.update_or_create(
                vendor=request.user.vendor,
                defaults={
                    'email': request.POST.get('paypal_email'),
                    'is_updated': True,
                }
            )
            messages.success(request, 'PayPal details updated successfully!')
        
        return redirect('vendor:dashboard')
    
    return redirect('vendor:payout_settings')