# customer/urls.py
from django.urls import path
from customer import views

app_name = "customer"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("orders/", views.orders, name="orders"),
    path("order_detail/<order_id>/", views.order_detail, name="order_detail"),
    path("order_item_detail/<order_id>/<item_id>/", views.order_item_detail, name="order_item_detail"),
    
    
    path("addresses/", views.addresses, name="addresses"),
    path("notis/", views.notis, name="notis"),
    path("mark_noti_seen/<id>/", views.mark_noti_seen, name="mark_noti_seen"),
    path("address_detail/<id>/", views.address_detail, name="address_detail"),
    path("address_create/", views.address_create, name="address_create"),
    path("set_default_address/<id>/", views.set_default_address, name="set_default_address"),
    path("delete_address/<id>/", views.delete_address, name="delete_address"),
    path("profile/", views.profile, name="profile"),
    path("change_password/", views.change_password, name="change_password"),
    
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/remove/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/count/', views.wishlist_count, name='wishlist_count'),
    path('wishlist/toggle/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/add/<int:id>/', views.add_to_wishlist, name='add_to_wishlist'),
]