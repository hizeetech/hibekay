# store/views.py
from django.http import HttpResponse
from django.shortcuts import redirect, render
from store import models as store_models
from django.contrib import messages
from store import forms as store_forms

from plugin.paginate_queryset import paginate_queryset



def index(request):
    products = store_models.Product.objects.filter(status="Published")
    categories = store_models.Category.objects.all()
    
    context = {
        "products": products,
        "categories": categories,
    }
    return render(request, "store/index.html", context)



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

