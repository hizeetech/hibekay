# userauths/urls.py
from django.urls import path
from userauths import views
from django.contrib.auth import views as auth_views
from userauths import views as userauths_views
from vendor import views as vendor_views
from customer import views as customer_views


app_name = "userauths"

urlpatterns = [
    path('sign-up/', userauths_views.register_view, name='sign-up'),
    path('sign-in/', userauths_views.login_view, name='sign-in'),
    path('logout/', views.logout_view, name='sign-out'),
    
    path('vendor/dashboard/', vendor_views.dashboard, name='vendor-dashboard'),
    path('customer/dashboard/', customer_views.dashboard, name='customer-dashboard'),

    #path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    #path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    #path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    #path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),    
    
    
]