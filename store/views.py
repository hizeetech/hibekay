# store/views.py
from decimal import Decimal
from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from store import models as store_models
from django.db import models
from customer import models as customer_models
from vendor import models as vendor_models
from django.contrib import messages
from django.db.models import Q, Avg, Sum
from plugin.tax_calculation import tax_calculation
from plugin.service_fee import calculate_service_fee
from django.conf import settings
from plugin.exchange_rate import convert_usd_to_inr, convert_usd_to_kobo, convert_usd_to_ngn, get_usd_to_ngn_rate
import razorpay # type: ignore
import stripe # type: ignore
import requests # type: ignore
from django.urls import reverse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives, send_mail
import json
from userauths import models as userauths_models
from plugin.paginate_queryset import paginate_queryset
from store import forms as store_forms
from django.core.paginator import Paginator
from .models import CartItem, Cart, Product
from . import models as store_models
import time
import base64
from django.contrib.auth.decorators import login_required

from .utils import get_cart_sub_total  # Make sure this function exists and works







# Create your views here.

stripe.api_key = settings.STRIPE_SECRET_KEY
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def clear_cart_items(request):
    try:
        cart_id = request.session['cart_id']
        store_models.Cart.objects.filter(cart_id=cart_id).delete()
    except:
        pass
    return


def index(request):
    products = store_models.Product.objects.filter(status="Published")
    categories = store_models.Category.objects.all()
    
    context = {
        "products": products,
        "categories": categories,
    }
    return render(request, "store/index.html", context)


def shop(request):
    products_list = store_models.Product.objects.filter(status="Published")
    categories = store_models.Category.objects.all()
    colors = store_models.VariantItem.objects.filter(variant__name='Color').values('title', 'content').distinct()
    sizes = store_models.VariantItem.objects.filter(variant__name='Size').values('title', 'content').distinct()
    item_display = [
        {"id": "1", "value": 1},
        {"id": "2", "value": 2},
        {"id": "3", "value": 3},
        {"id": "40", "value": 40},
        {"id": "50", "value": 50},
        {"id": "100", "value": 100},
    ]

    ratings = [
        {"id": "1", "value": "★☆☆☆☆"},
        {"id": "2", "value": "★★☆☆☆"},
        {"id": "3", "value": "★★★☆☆"},
        {"id": "4", "value": "★★★★☆"},
        {"id": "5", "value": "★★★★★"},
    ]

    prices = [
        {"id": "lowest", "value": "Highest to Lowest"},
        {"id": "highest", "value": "Lowest to Highest"},
    ]


    print(sizes)

    products = paginate_queryset(request, products_list, 10)

    context = {
        "products": products,
        "products_list": products_list,
        "categories": categories,
        'colors': colors,
        'sizes': sizes,
        'item_display': item_display,
        'ratings': ratings,
        'prices': prices,
    }
    return render(request, "store/shop.html", context)


def search_products(request):
    search_term = request.GET.get('search', '')
    category_ids = request.GET.get('categories', '').split(',') if request.GET.get('categories') else []
    
    # Start with all products
    products = Product.objects.all()
    
    # Apply search filter
    if search_term:
        products = products.filter(
            Q(name__icontains=search_term) | 
            Q(description__icontains=search_term)
        )
    else:
        # If no search term, return all products (or apply other default filters)
        products = products.all()
    
    # Apply category filter
    if category_ids and category_ids[0]:
        products = products.filter(category__id__in=category_ids)
    
    # Add other filters as needed (price, rating, etc.)
    
    # Paginate results
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Render the product list HTML
    html = render_to_string('store/partials/product_list.html', {
        'products': page_obj
    })
    
    return JsonResponse({
        'html': html,
        'count': products.count()
    })

def category(request, id):
    category = store_models.Category.objects.get(id=id)
    products_list = store_models.Product.objects.filter(status="Published", category=category)

    query = request.GET.get("q")
    if query:
        products_list = products_list.filter(name__icontains=query)

    products = paginate_queryset(request, products_list, 10)

    context = {
        "products": products,
        "products_list": products_list,
        "category": category,
    }
    return render(request, "store/category.html", context)


from store.decorators import vendor_required

@vendor_required
def create_category(request):
    if not request.user.is_authenticated:
        messages.warning(request, "You need to be logged in to create categories.")
        return redirect("userauths:sign-in")
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != "Vendor":
        messages.warning(request, "You need to be a vendor to create categories.")
        return redirect("userauths:sign-in")

    if request.method == "POST":
        form = store_forms.CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                category = form.save(commit=False)
                category.vendor = request.user  # This sets the vendor
                category.save()  # Now save with vendor set
                messages.success(request, "Category created successfully!")
                return redirect("userauths:vendor-dashboard")
            except Exception as e:
                messages.error(request, f"Error creating category: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = store_forms.CategoryForm()
    
    return render(request, "store/create_category.html", {'form': form})

def vendors(request):
    vendors = userauths_models.Profile.objects.filter(user_type="Vendor")
    
    context = {
        "vendors": vendors
    }
    return render(request, "store/vendors.html", context)



def product_detail(request, slug):
    product = store_models.Product.objects.get(status="Published", slug=slug)
    product_stock_range = range(1, product.stock + 1)

    related_products = store_models.Product.objects.filter(category=product.category, status="Published").exclude(id=product.id)

    context = {
        "product": product,
        "product_stock_range": product_stock_range,
        "related_products": related_products,
    }
    return render(request, "store/product_detail.html", context)


def add_to_cart(request):
    # Get parameters from the request (ID, color, size, quantity, cart_id)
    id = request.GET.get("id")
    qty = request.GET.get("qty")
    color = request.GET.get("color")
    size = request.GET.get("size")
    cart_id = request.GET.get("cart_id")

    request.session['cart_id'] = cart_id

    # Validate required fields
    if not id or not qty or not cart_id:
        return JsonResponse({"error": "No color or size selected"}, status=400)

    # Try to fetch the product, return an error if it doesn't exist
    try:
        product = store_models.Product.objects.get(status="Published", id=id)
    except store_models.Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    # Check if the item is already in the cart
    existing_cart_item = store_models.Cart.objects.filter(cart_id=cart_id, product=product).first()

    # Check if quantity that user is adding exceed item stock qty
    if int(qty) > product.stock:
        return JsonResponse({"error": "Qty exceed current stock amount"}, status=404)

    # If the item is not in the cart, create a new cart entry
    if not existing_cart_item:
        cart = store_models.Cart()
        cart.product = product
        cart.qty = qty
        cart.price = product.price
        cart.color = color
        cart.size = size
        cart.sub_total = Decimal(product.price) * Decimal(qty)
        cart.shipping = Decimal(product.shipping) * Decimal(qty)
        cart.total = cart.sub_total + cart.shipping
        cart.user = request.user if request.user.is_authenticated else None
        cart.cart_id = cart_id
        cart.save()

        message = "Item added to cart"
    else:
        # If the item exists in the cart, update the existing entry
        existing_cart_item.color = color
        existing_cart_item.size = size
        existing_cart_item.qty = qty
        existing_cart_item.price = product.price
        existing_cart_item.sub_total = Decimal(product.price) * Decimal(qty)
        existing_cart_item.shipping = Decimal(product.shipping) * Decimal(qty)
        existing_cart_item.total = existing_cart_item.sub_total +  existing_cart_item.shipping
        existing_cart_item.user = request.user if request.user.is_authenticated else None
        existing_cart_item.cart_id = cart_id
        existing_cart_item.save()

        message = "Cart updated"

    # Count the total number of items in the cart
    total_cart_items = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user if request.user.is_authenticated else None))
    cart_sub_total = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user if request.user.is_authenticated else None)).aggregate(sub_total = Sum("sub_total"))['sub_total'] or Decimal('0.00')

    # Return the response with the cart update message and total cart items
    return JsonResponse({
        "message": message ,
        "total_cart_items": total_cart_items.count(),
        "cart_sub_total": "{:,.2f}".format(cart_sub_total),
        "item_sub_total": "{:,.2f}".format(existing_cart_item.sub_total) if existing_cart_item else "{:,.2f}".format(cart.sub_total)
    })


from django.shortcuts import render, redirect
from django.db.models import Q, Sum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from store import models as store_models
from customer import models as customer_models

@login_required
def cart(request):
    """
    Enhanced cart view with better address handling and user flow
    """
    try:
        # Get cart items (combines session cart and user cart if authenticated)
        cart_filter = Q(cart_id=request.session.get('cart_id'))
        if request.user.is_authenticated:
            cart_filter |= Q(user=request.user)
            
        items = store_models.Cart.objects.filter(cart_filter).select_related(
            'product', 
            'product__vendor__profile'
        )
        
        # Handle empty cart case first
        if not items.exists():
            messages.info(request, "Your cart is empty")
            return redirect("store:index")

        # Calculate cart total
        cart_sub_total = items.aggregate(
            sub_total=Sum("sub_total")
        )['sub_total'] or Decimal('0.00')

        # Address handling - only check if user is authenticated
        addresses = customer_models.Address.objects.filter(user=request.user)
        address_required = False
        
        if not addresses.exists():
            messages.info(request, "Please add a delivery address to proceed")
            return redirect('customer:address_create')
        elif not addresses.filter(is_default=True).exists():
            messages.info(request, "Please set a default delivery address")
            request.session['cart_redirect'] = True  # Flag to return to cart after address setup
            return redirect('customer:addresses')

        # Get personalized product suggestions
        suggested_products = get_suggested_products(items) if items.exists() else []

        context = {
            "items": items,
            "cart_sub_total": cart_sub_total,
            "addresses": addresses,
            "suggested_products": suggested_products,
        }
        return render(request, "store/cart.html", context)

    except Exception as e:
        messages.error(request, "An error occurred while loading your cart")
        # Log the error here if you have logging setup
        return redirect("store:index")

def get_suggested_products(cart_items):
    """Helper function to get suggested products based on cart items"""
    vendor_ids = cart_items.filter(
        product__vendor__isnull=False
    ).values_list(
        'product__vendor__id', 
        flat=True
    ).distinct()

    if not vendor_ids:
        return []

    cart_product_ids = cart_items.values_list('product__id', flat=True)
    
    return store_models.Product.objects.filter(
        vendor__id__in=vendor_ids,
        status="Published"
    ).exclude(
        id__in=cart_product_ids
    ).order_by('-date')[:6]


def delete_cart_item(request):
    id = request.GET.get("id")
    item_id = request.GET.get("item_id")
    cart_id = request.GET.get("cart_id")
    
    # Validate required fields
    if not id and not item_id and not cart_id:
        return JsonResponse({"error": "Item or Product id not found"}, status=400)

    try:
        product = store_models.Product.objects.get(status="Published", id=id)
    except store_models.Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    # Check if the item is already in the cart
    item = store_models.Cart.objects.get(product=product, id=item_id)
    item.delete()

    # Count the total number of items in the cart
    total_cart_items = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user))
    cart_sub_total = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user)).aggregate(sub_total = models.Sum("sub_total"))['sub_total']

    return JsonResponse({
        "message": "Item deleted",
        "total_cart_items": total_cart_items.count(),
        "cart_sub_total": "{:,.2f}".format(cart_sub_total) if cart_sub_total else 0.00
    })
    


@csrf_exempt
@login_required
def remove_cart_item(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')

        try:
            item = CartItem.objects.get(id=item_id, cart__user=request.user)
            item.delete()

            cart = Cart.objects.get(user=request.user)
            cart_sub_total = cart.get_cart_total()

            return JsonResponse({
                'success': True,
                'cartSubTotal': cart_sub_total
            })
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@csrf_exempt
@login_required
def update_cart_item(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        update_type = request.POST.get('update_type')
        cart_id = request.session.get('cart_id')

        try:
            # Use Cart model instead of CartItem since that's what your system is using
            item = Cart.objects.get(id=item_id, cart_id=cart_id)
            
            if update_type == 'increase':
                item.qty += 1
            elif update_type == 'decrease':
                item.qty -= 1

            if item.qty < 1:
                item.delete()
                return JsonResponse({
                    'success': True,
                    'item_deleted': True,
                    'item_id': item_id,
                    'cartSubTotal': Cart.get_cart_total(cart_id)
                })
            else:
                item.save()
                cart_sub_total = Cart.get_cart_total(cart_id)
                return JsonResponse({
                    'success': True,
                    'item_qty': item.qty,
                    'item_sub_total': float(item.sub_total),
                    'cartSubTotal': cart_sub_total,
                    'item_deleted': False,
                    'item_id': item_id
                })
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


    
    
def create_order(request):
    if request.method == "POST":
        address_id = request.POST.get("address")
        if not address_id:
            messages.warning(request, "Please select an address to continue")
            return redirect("store:cart")
        
        address = customer_models.Address.objects.filter(user=request.user, id=address_id).first()

        if "cart_id" in request.session:
            cart_id = request.session['cart_id']
        else:
            cart_id = None

        items = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user) if request.user.is_authenticated else Q(cart_id=cart_id))
        cart_sub_total = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user) if request.user.is_authenticated else Q(cart_id=cart_id)).aggregate(sub_total = models.Sum("sub_total"))['sub_total']
        cart_shipping_total = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user) if request.user.is_authenticated else Q(cart_id=cart_id)).aggregate(shipping = models.Sum("shipping"))['shipping']
        
        order = store_models.Order()
        order.sub_total = cart_sub_total
        order.customer = request.user
        order.address = address
        order.shipping = cart_shipping_total
        order.tax = tax_calculation(address.country, cart_sub_total)
        order.total = order.sub_total + order.shipping + Decimal(order.tax)
        order.service_fee = calculate_service_fee(order.total)
        order.total += order.service_fee
        order.initial_total = order.total
        order.save()

        for i in items:
            store_models.OrderItem.objects.create(
                order=order,
                product=i.product,
                qty=i.qty,
                color=i.color,
                size=i.size,
                price=i.price,
                sub_total=i.sub_total,
                shipping=i.shipping,
                tax=tax_calculation(address.country, i.sub_total),
                total=i.total,
                initial_total=i.total,
                vendor=i.product.vendor
            )

            order.vendors.add(i.product.vendor)
        
    
    return redirect("store:checkout", order.order_id)



def coupon_apply(request, order_id):
    print("Order Id ========", order_id)
    
    try:
        order = store_models.Order.objects.get(order_id=order_id)
        order_items = store_models.OrderItem.objects.filter(order=order)
    except store_models.Order.DoesNotExist:
        messages.error(request, "Order not found")
        return redirect("store:cart")

    if request.method == 'POST':
        coupon_code = request.POST.get("coupon_code")
        
        if not coupon_code:
            messages.error(request, "No coupon entered")
            return redirect("store:checkout", order.order_id)
            
        try:
            coupon = store_models.Coupon.objects.get(code=coupon_code)
        except store_models.Coupon.DoesNotExist:
            messages.error(request, "Coupon does not exist")
            return redirect("store:checkout", order.order_id)
        
        if coupon in order.coupons.all():
            messages.warning(request, "Coupon already activated")
            return redirect("store:checkout", order.order_id)
        else:
            # Assuming coupon applies to specific vendor items, not globally
            total_discount = 0
            for item in order_items:
                if coupon.vendor == item.product.vendor and coupon not in item.coupon.all():
                    item_discount = item.total * coupon.discount / 100  # Discount for this item
                    total_discount += item_discount

                    item.coupon.add(coupon) 
                    item.total -= item_discount
                    item.saved += item_discount
                    item.save()

            # Apply total discount to the order after processing all items
            if total_discount > 0:
                order.coupons.add(coupon)
                order.total -= total_discount
                order.sub_total -= total_discount
                order.saved += total_discount
                order.save()
        
        messages.success(request, "Coupon Activated")
        return redirect("store:checkout", order.order_id)



def checkout(request, order_id):
    """
    Renders the checkout page with order details, amount in NGN, and payment gateway configurations.
    """
    order = store_models.Order.objects.get(order_id=order_id)

    # Calculate amount in Kobo (NGN)
    amount_in_kobo = int(order.total * 100)  # Convert NGN to Kobo

    try:
        # Create a Razorpay order in NGN
        razorpay_order = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)).order.create({
            "amount": amount_in_kobo,
            "currency": "NGN",
            "payment_capture": "1"
        })
    except Exception as e:
        print(f"Razorpay error: {e}")
        razorpay_order = None

    context = {
        "order": order,
        "amount_in_kobo": amount_in_kobo,
        "amount_in_ngn": order.total,  # Display the original NGN amount
        "razorpay_order_id": razorpay_order['id'] if razorpay_order else None,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "paypal_client_id": settings.PAYPAL_CLIENT_ID,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "paystack_public_key": settings.PAYSTACK_PUBLIC_KEY,
        "flutterwave_public_key": settings.FLUTTERWAVE_PUBLIC_KEY,
        'MONNIFY_API_KEY': settings.MONNIFY_API_KEY,
        'MONNIFY_CONTRACT_CODE': settings.MONNIFY_CONTRACT_CODE,      
        
    }

    return render(request, "store/checkout.html", context)


# Remove all functions that were converting from USD to other currencies.
# Remove the fetch_exchange_rates function.

@csrf_exempt
def stripe_payment(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)
    stripe.api_key = settings.STRIPE_SECRET_KEY

    checkout_session = stripe.checkout.Session.create(
        customer_email = order.address.email,
        payment_method_types=['card'],
        line_items = [
            {
                'price_data': {
                    'currency': 'USD',
                    'product_data': {
                        'name': order.address.full_name
                    },
                    'unit_amount': int(order.total * 100)
                },
                'quantity': 1
            }
        ],
        mode = 'payment',
        success_url = request.build_absolute_uri(reverse("store:stripe_payment_verify", args=[order.order_id])) + "?session_id={CHECKOUT_SESSION_ID}" + "&payment_method=Stripe",
        cancel_url = request.build_absolute_uri(reverse("store:stripe_payment_verify", args=[order.order_id]))
    )

    print("checkkout session", checkout_session)
    return JsonResponse({"sessionId": checkout_session.id})

def stripe_payment_verify(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)

    session_id = request.GET.get("session_id")
    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status == "paid":
        if order.payment_status == "Processing":
            order.payment_status = "Paid"
            order.save()
            clear_cart_items(request)
            
            
            customer_merge_data = {
                'order': order,
                'order_items': order.order_items(),
            }
            subject = f"New Order!"
            text_body = render_to_string("email/order/customer/customer_new_order.txt", customer_merge_data)
            html_body = render_to_string("email/order/customer/customer_new_order.html", customer_merge_data)

            msg = EmailMultiAlternatives(
                subject=subject, from_email=settings.FROM_EMAIL,
                to=[order.address.email], body=text_body
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()
            
            customer_models.Notifications.objects.create(type="New Order", user=request.user)

            # Send Order Emails to Vendors
            for item in order.order_items():
                
                vendor_merge_data = {
                    'item': item,
                }
                subject = f"New Order!"
                text_body = render_to_string("email/order/vendor/vendor_new_order.txt", vendor_merge_data)
                html_body = render_to_string("email/order/vendor/vendor_new_order.html", vendor_merge_data)

                msg = EmailMultiAlternatives(
                    subject=subject, from_email=settings.FROM_EMAIL,
                    to=[item.vendor.email], body=text_body
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send()
                
                vendor_models.Notifications.objects.create(type="New Order", user=item.vendor, order=item)

            return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
    
    return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


def get_paypal_access_token():
    token_url = 'https://api.sandbox.paypal.com/v1/oauth2/token'
    data = {'grant_type': 'client_credentials'}
    auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_ID)
    response = requests.post(token_url, data=data, auth=auth)

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f'Failed to get access token from PayPal. Status code: {response.status_code}') 
    

def paypal_payment_verify(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)

    transaction_id = request.GET.get("transaction_id")
    paypal_api_url = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{transaction_id}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {get_paypal_access_token()}',
    }
    response = requests.get(paypal_api_url, headers=headers)

    if response.status_code == 200:
        paypal_order_data = response.json()
        paypal_payment_status = paypal_order_data['status']
        #payment_method = 'PayPal'
        if paypal_payment_status == 'COMPLETED':
            if order.payment_status == "Processing":
                order.payment_status = "Paid"
                payment_method = request.GET.get("payment_method")
                order.payment_method = payment_method
                order.save()
                clear_cart_items(request)
                
                customer_merge_data = {
                'order': order,
                'order_items': order.order_items(),
                }
                subject = f"New Order!"
                text_body = render_to_string("email/order/customer/customer_new_order.txt", customer_merge_data)
                html_body = render_to_string("email/order/customer/customer_new_order.html", customer_merge_data)

                msg = EmailMultiAlternatives(
                    subject=subject, from_email=settings.FROM_EMAIL,
                    to=[order.address.email], body=text_body
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send()
                
                customer_models.Notifications.objects.create(type="New Order", user=request.user)

                # Send Order Emails to Vendors
                for item in order.order_items():
                    
                    vendor_merge_data = {
                        'item': item,
                    }
                    subject = f"New Order!"
                    text_body = render_to_string("email/order/vendor/vendor_new_order.txt", vendor_merge_data)
                    html_body = render_to_string("email/order/vendor/vendor_new_order.html", vendor_merge_data)

                    msg = EmailMultiAlternatives(
                        subject=subject, from_email=settings.FROM_EMAIL,
                        to=[item.vendor.email], body=text_body
                    )
                    msg.attach_alternative(html_body, "text/html")
                    msg.send()
                    
                    vendor_models.Notifications.objects.create(type="New Order", user=item.vendor, order=item)
            
                return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


def paystack_payment_verify(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)
    reference = request.GET.get('reference', '')

    if reference:
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_PRIVATE_KEY}",
            "Content-Type": "application/json"
        }

        # Verify the transaction
        response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
        response_data = response.json()

        if response_data['status']:
            if response_data['data']['status'] == 'success':
                if order.payment_status == "Processing":
                    order.payment_status = "Paid"
                    payment_method = request.GET.get("payment_method")
                    order.payment_method = payment_method
                    order.save()
                    clear_cart_items(request)
                    
                    customer_merge_data = {
                    'order': order,
                    'order_items': order.order_items(),
                    }
                    subject = f"New Order!"
                    text_body = render_to_string("email/order/customer/customer_new_order.txt", customer_merge_data)
                    html_body = render_to_string("email/order/customer/customer_new_order.html", customer_merge_data)

                    msg = EmailMultiAlternatives(
                        subject=subject, from_email=settings.FROM_EMAIL,
                        to=[order.address.email], body=text_body
                    )
                    msg.attach_alternative(html_body, "text/html")
                    msg.send()
                    
                    customer_models.Notifications.objects.create(type="New Order", user=request.user)
            
                    # Send Order Emails to Vendors
                    for item in order.order_items():
                        
                        vendor_merge_data = {
                            'item': item,
                        }
                        subject = f"New Order!"
                        text_body = render_to_string("email/order/vendor/vendor_new_order.txt", vendor_merge_data)
                        html_body = render_to_string("email/order/vendor/vendor_new_order.html", vendor_merge_data)

                        msg = EmailMultiAlternatives(
                            subject=subject, from_email=settings.FROM_EMAIL,
                            to=[item.vendor.email], body=text_body
                        )
                        msg.attach_alternative(html_body, "text/html")
                        msg.send()
                        
                        vendor_models.Notifications.objects.create(type="New Order", user=item.vendor, order=item)
            
                    return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
                else:
                    return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
            else:
                # Payment failed
                return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
        else:
            return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
    

# views.py
@csrf_exempt
def paystack_webhook(request):
    payload = json.loads(request.body)
    if payload['event'] == 'charge.success':
        order_id = payload['data']['metadata']['order_id']
        order = store_models.Order.objects.get(order_id=order_id)
        order.payment_status = "Paid"
        order.save()
    return HttpResponse(status=200)


def monnify_payment(request, order_id):
    """
    Initialize Monnify payment and return checkout URL
    """
    try:
        order = store_models.Order.objects.get(order_id=order_id)

        if order.payment_status != "Processing":
            return JsonResponse({'status': 'error', 'message': 'Order is not in a payable state'}, status=400)

        api_key = settings.MONNIFY_API_KEY
        secret_key = settings.MONNIFY_SECRET_KEY
        contract_code = settings.MONNIFY_CONTRACT_CODE
        base_url = settings.MONNIFY_BASE_URL

        # Generate Basic Auth token
        auth_string = f"{api_key}:{secret_key}"
        basic_auth_token = base64.b64encode(auth_string.encode()).decode()

        # Generate unique payment reference
        payment_reference = f"ORDER-{order.order_id}-{int(time.time())}"

        # Build callback URL
        callback_url = request.build_absolute_uri(reverse("store:monnify_payment_callback", args=[order.order_id]))

        payment_data = {
            "amount": float(order.total),
            "customerName": order.address.full_name,
            "customerEmail": order.address.email,
            "paymentReference": payment_reference,
            "paymentDescription": f"Payment for Order #{order.order_id}",
            "currencyCode": "NGN",
            "contractCode": contract_code,
            "redirectUrl": callback_url,
            "paymentMethods": ["CARD", "ACCOUNT_TRANSFER", "USSD"],
            "metadata": {"order_id": str(order.order_id)}
        }

        # Authenticate and get access token
        auth_response = requests.post(
            f"{base_url}/api/v1/auth/login",
            headers={"Authorization": f"Basic {basic_auth_token}"},
            timeout=10
        )
        auth_response.raise_for_status()
        access_token = auth_response.json()['responseBody']['accessToken']

        # Initialize transaction
        transaction_url = f"{base_url}/api/v1/merchant/transactions/init-transaction"
        transaction_response = requests.post(
            transaction_url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=payment_data,
            timeout=10
        )
        transaction_response.raise_for_status()

        checkout_url = transaction_response.json()['responseBody']['checkoutUrl']

        # Save payment reference to order
        order.payment_reference = payment_reference
        order.save()
        clear_cart_items(request)
        
        customer_merge_data = {
        'order': order,
        'order_items': order.order_items(),
        }
        subject = f"New Order!"
        text_body = render_to_string("email/order/customer/customer_new_order.txt", customer_merge_data)
        html_body = render_to_string("email/order/customer/customer_new_order.html", customer_merge_data)

        msg = EmailMultiAlternatives(
            subject=subject, from_email=settings.FROM_EMAIL,
            to=[order.address.email], body=text_body
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        
        customer_models.Notifications.objects.create(type="New Order", user=request.user)
        
        #Send Order Emails to Vendors
        for item in order.order_items():
            
            vendor_merge_data = {
                'item': item,
            }
            subject = f"New Order!"
            text_body = render_to_string("email/order/vendor/vendor_new_order.txt", vendor_merge_data)
            html_body = render_to_string("email/order/vendor/vendor_new_order.html", vendor_merge_data)

            msg = EmailMultiAlternatives(
                subject=subject, from_email=settings.FROM_EMAIL,
                to=[item.vendor.email], body=text_body
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()
            
            vendor_models.Notifications.objects.create(type="New Order", user=item.vendor, order=item)

        return JsonResponse({'status': 'success', 'redirectUrl': checkout_url})

    except store_models.Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def monnify_payment_callback(request, order_id):
    """
    Handle Monnify payment callback after payment completion
    """
    try:
        order = store_models.Order.objects.get(order_id=order_id)
        payment_reference = request.GET.get('paymentReference')

        if not payment_reference:
            return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")

        # Verify payment
        auth_string = f"{settings.MONNIFY_API_KEY}:{settings.MONNIFY_SECRET_KEY}"
        basic_auth_token = base64.b64encode(auth_string.encode()).decode()

        auth_response = requests.post(
            f"{settings.MONNIFY_BASE_URL}/api/v1/auth/login",
            headers={"Authorization": f"Basic {basic_auth_token}"},
            timeout=10
        )
        auth_response.raise_for_status()
        access_token = auth_response.json()['responseBody']['accessToken']

        verify_url = f"{settings.MONNIFY_BASE_URL}/api/v1/merchant/transactions/query?paymentReference={payment_reference}"
        verify_response = requests.get(
            verify_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        verify_response.raise_for_status()
        response_data = verify_response.json()

        if response_data['responseBody']['paymentStatus'] == "PAID":
            order.payment_status = "Paid"
            order.payment_method = "Monnify"
            order.save()
            clear_cart_items(request)
            
            customer_merge_data = {
            'order': order,
            'order_items': order.order_items(),
            }
            subject = f"New Order!"
            text_body = render_to_string("email/order/customer/customer_new_order.txt", customer_merge_data)
            html_body = render_to_string("email/order/customer/customer_new_order.html", customer_merge_data)

            msg = EmailMultiAlternatives(
                subject=subject, from_email=settings.FROM_EMAIL,
                to=[order.address.email], body=text_body
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()
            
            customer_models.Notifications.objects.create(type="New Order", user=request.user)
            
            #Send Order Emails to Vendors
            for item in order.order_items():
                
                vendor_merge_data = {
                    'item': item,
                }
                subject = f"New Order!"
                text_body = render_to_string("email/order/vendor/vendor_new_order.txt", vendor_merge_data)
                html_body = render_to_string("email/order/vendor/vendor_new_order.html", vendor_merge_data)

                msg = EmailMultiAlternatives(
                    subject=subject, from_email=settings.FROM_EMAIL,
                    to=[item.vendor.email], body=text_body
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send()
                
                vendor_models.Notifications.objects.create(type="New Order", user=item.vendor, order=item)
            
            return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")

        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")

    except store_models.Order.DoesNotExist:
        return redirect("store:index")
    except Exception as e:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


@csrf_exempt
def monnify_webhook(request):
    """
    Handle Monnify webhook events
    """
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            if payload.get('eventType') == 'SUCCESSFUL_TRANSACTION':
                payment_reference = payload['data']['paymentReference']

                auth_string = f"{settings.MONNIFY_API_KEY}:{settings.MONNIFY_SECRET_KEY}"
                basic_auth_token = base64.b64encode(auth_string.encode()).decode()

                auth_response = requests.post(
                    f"{settings.MONNIFY_BASE_URL}/api/v1/auth/login",
                    headers={"Authorization": f"Basic {basic_auth_token}"},
                    timeout=5
                )
                auth_response.raise_for_status()
                access_token = auth_response.json()['responseBody']['accessToken']

                verify_response = requests.get(
                    f"{settings.MONNIFY_BASE_URL}/api/v1/merchant/transactions/query?paymentReference={payment_reference}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=5
                )
                verify_response.raise_for_status()

                if verify_response.json()['responseBody']['paymentStatus'] == "PAID":
                    order = store_models.Order.objects.get(payment_reference=payment_reference)
                    if order.payment_status != "Paid":
                        order.payment_status = "Paid"
                        order.payment_method = "Monnify"
                        order.save()
                        clear_cart_items(request)

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error'}, status=405)



''' def flutterwave_payment_callback(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)

    payment_id = request.GET.get('tx_ref')
    status = request.GET.get('status')

    headers = {
        'Authorization': f'Bearer {settings.FLUTTERWAVE_PRIVATE_KEY}'
    }
    response = requests.get(f'https://api.flutterwave.com/v3/charges/verify_by_id/{payment_id}', headers=headers)

    if response.status_code == 200:
        if order.payment_status == "Processing":
            order.payment_status = "Paid"
            payment_method = request.GET.get("payment_method")
            order.payment_method = payment_method
            order.save()
            
            # Send Order Emails to Customers
            
            # Send InApp Notification
            
            # Send Email to Vendor
            
            return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
        else:
            return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed") '''
    
    
    
def flutterwave_payment_callback(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)
    tx_ref = request.GET.get('tx_ref', "")
    

    headers = {
        'Authorization': f'Bearer {settings.FLUTTERWAVE_PRIVATE_KEY}',
        "Content-Type": "application/json"
    }
    response = requests.get(f'https://api.flutterwave.com/v3/transactions/verify_by_reference?tx_ref={tx_ref}', headers=headers)
    response_data = response.json()

    if response_data['data']['status'] == "successful":
        if order.payment_status == "Processing":
            order.payment_status = "Paid"
            #payment_method = request.GET.get("payment_method")
            #order.payment_method = payment_method
            order.save()
            clear_cart_items(request)
            
            # Send Order Emails to Customers
            
            # Send InApp Notification
            
            # Send Email to Vendor
            
            return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
        
    
    return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


    
def payment_status(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)
    payment_status = request.GET.get("payment_status", "unknown")  # Default to "unknown"

    context = {
        "order": order,
        "payment_status": payment_status,
    }

    if payment_status == "unknown":
        if order.payment_status == "Paid":
            context["payment_status"] = "paid"
        else:
            context["payment_status"] = "failed"
        print(f"Payment status for order {order_id} is unknown. Order table status is {order.payment_status}")

    return render(request, "store/payment_status.html", context)


def filter_products(request):
    products = store_models.Product.objects.all()

    # Get filters from the AJAX request
    categories = request.GET.getlist('categories[]')
    rating = request.GET.getlist('rating[]')
    sizes = request.GET.getlist('sizes[]')
    colors = request.GET.getlist('colors[]')
    price_order = request.GET.get('prices')
    search_filter = request.GET.get('searchFilter')
    display = request.GET.get('display')

    print("categories =======", categories)
    print("rating =======", rating)
    print("sizes =======", sizes)
    print("colors =======", colors)
    print("price_order =======", price_order)
    print("search_filter =======", search_filter)
    print("display =======", display)


    # Apply category filtering
    if categories:
        products = products.filter(category__id__in=categories)

    # Apply rating filtering
    if rating:
        products = products.filter(reviews__rating__in=rating).distinct()

    

    # Apply size filtering
    if sizes:
        products = products.filter(variant__variant_items__content__in=sizes).distinct()

    # Apply color filtering
    if colors:
        products = products.filter(variant__variant_items__content__in=colors).distinct()

    # Apply price ordering
    if price_order == 'lowest':
        products = products.order_by('-price')
    elif price_order == 'highest':
        products = products.order_by('price')

    # Apply search filter
    if search_filter:
        products = products.filter(name__icontains=search_filter)

    if display:
        products = products.filter()[:int(display)]


    # Render the filtered products as HTML using render_to_string
    html = render_to_string('partials/_store.html', {'products': products})

    return JsonResponse({'html': html, 'product_count': products.count()})

def order_tracker_page(request):
    if request.method == "POST":
        item_id = request.POST.get("item_id")
        return redirect("store:order_tracker_detail", item_id)
    
    return render(request, "store/order_tracker_page.html")

def order_tracker_detail(request, item_id):
    try:
        item = store_models.OrderItem.objects.filter(models.Q(item_id=item_id) | models.Q(tracking_id=item_id)).first()
    except:
        item = None
        messages.error(request, "Order not found!")
        return redirect("store:order_tracker_page")
    
    context = {
        "item": item,
    }
    return render(request, "store/order_tracker.html", context)

def about(request):
    return render(request, "pages/about.html")

def contact(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        userauths_models.ContactMessage.objects.create(
            full_name=full_name,
            email=email,
            subject=subject,
            message=message,
        )
        messages.success(request, "Message sent successfully")
        return redirect("store:contact")
    return render(request, "pages/contact.html")

def faqs(request):
    return render(request, "pages/faqs.html")

def privacy_policy(request):
    return render(request, "pages/privacy_policy.html")

def terms_conditions(request):
    return render(request, "pages/terms_conditions.html")



from .models import CartItem, Cart, Product, Category
from django.core.exceptions import PermissionDenied

@login_required
def markethub(request):
    # Check if user is a customer
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != "Customer":
        raise PermissionDenied("Only customers can access Markethub")
    
    # Get all active categories with at least one active product
    categories = Category.objects.filter(
        active=True,
        products__status="Published",
        products__active=True
    ).distinct()
    
    featured_products = Product.objects.filter(
        featured=True, 
        active=True,
        status="Published"
    ).select_related('vendor', 'category')
    
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'markethub_categories': categories,  # For navbar dropdown
    }
    return render(request, 'store/markethub.html', context)

@login_required
def markethub_category(request, category_id):
    # Check if user is a customer
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != "Customer":
        raise PermissionDenied("Only customers can access Markethub")
    
    category = get_object_or_404(Category, id=category_id, active=True)
    products = Product.objects.filter(
        category=category,
        active=True,
        status="Published"
    ).select_related('vendor')
    
    categories = Category.objects.filter(
        active=True,
        products__status="Published",
        products__active=True
    ).distinct()
    
    context = {
        'category': category,
        'products': products,
        'categories': categories,
        'markethub_categories': categories,
    }
    return render(request, 'store/markethub_category.html', context)