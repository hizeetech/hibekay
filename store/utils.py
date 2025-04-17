# store/utils.py
# store/utils.py
from .models import CartItem

def get_cart_sub_total(user):
    cart_items = CartItem.objects.filter(user=user)
    total = sum(item.product.price * item.quantity for item in cart_items)
    return round(total, 2)
