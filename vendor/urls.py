# vendor/urls.py
from django.urls import path
from vendor import views
from vendor.admin import approve_vendor, reject_vendor  # Import the admin views

app_name = "vendor"

urlpatterns = [
    # Dashboard and approval
    path("dashboard/", views.dashboard, name="dashboard"),
    path("approval-pending/", views.approval_pending, name="approval-pending"),
    
    # Admin approval URLs
    path('admin/approve-vendor/<int:vendor_id>/', approve_vendor, name='approve_vendor'),
    path('admin/reject-vendor/<int:vendor_id>/', reject_vendor, name='reject_vendor'),

    
    # Product management
    path("products/", views.products, name="products"),
    path("create_product/", views.create_product, name="create_product"),
    path("update_product/<int:id>/", views.update_product, name="update_product"),
    path("delete_product/<int:product_id>/", views.delete_product, name="delete_product"),
    path("delete_product_image/<int:product_id>/<int:image_id>/", views.delete_product_image, name="delete_product_image"),
    
    # Variant management
    path("delete_variants/<int:product_id>/<int:variant_id>/", views.delete_variants, name="delete_variants"),
    path("delete_variants_items/<int:variant_id>/<int:item_id>/", views.delete_variants_items, name="delete_variants_items"),
    
    # Order management
    path("orders/", views.orders, name="orders"),
    path("order_detail/<str:order_id>/", views.order_detail, name="order_detail"),
    path("order_item_detail/<str:order_id>/<str:item_id>/", views.order_item_detail, name="order_item_detail"),
    path("update_order_status/<str:order_id>/", views.update_order_status, name="update_order_status"),
    path("update_order_item_status/<str:order_id>/<str:item_id>/", views.update_order_item_status, name="update_order_item_status"),
    
    # Category management
    path("categories/", views.categories, name="categories"),
    path("category/<int:id>/", views.category_detail, name="category_detail"),
    path("update_category/<int:id>/", views.update_category, name="update_category"),
    path("delete_category/<int:id>/", views.delete_category, name="delete_category"),
    
    # Coupon management
    path("coupons/", views.coupons, name="coupons"),
    path("update_coupon/<int:id>/", views.update_coupon, name="update_coupon"),
    path("delete_coupon/<int:id>/", views.delete_coupon, name="delete_coupon"),
    path("create_coupon/", views.create_coupon, name="create_coupon"),
    
    # Reviews and notifications
    path("reviews/", views.reviews, name="reviews"),
    path("update_reply/<int:id>/", views.update_reply, name="update_reply"),
    path("notis/", views.notis, name="notis"),
    path("mark_noti_seen/<int:id>/", views.mark_noti_seen, name="mark_noti_seen"),
    
    # Profile and settings
    path("profile/", views.profile, name="profile"),
    path("change_password/", views.change_password, name="change_password"),
    path("settings/", views.settings, name="settings"),
    
    path('payout-settings/', views.payout_settings, name='payout_settings'),
    path('save-payout-settings/', views.save_payout_settings, name='save_payout_settings'),
    
    
]