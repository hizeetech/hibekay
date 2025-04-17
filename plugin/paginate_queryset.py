# plugin/paginate_queryset.py
from django.core.paginator import Paginator
from store.models import Coupon  # Assuming Coupon is in store.models

def paginate_queryset(request, queryset, per_page):    
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
