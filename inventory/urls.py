from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.otp_request_view, name='otp_request'),
    path('reset-password/', views.otp_verify_view, name='otp_verify'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/new/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),

    # Receipts
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/new/', views.receipt_create, name='receipt_create'),
    path('receipts/<int:pk>/', views.receipt_detail, name='receipt_detail'),
    path('receipts/<int:pk>/validate/', views.receipt_validate, name='receipt_validate'),

    # Deliveries
    path('deliveries/', views.delivery_list, name='delivery_list'),
    path('deliveries/new/', views.delivery_create, name='delivery_create'),
    path('deliveries/<int:pk>/', views.delivery_detail, name='delivery_detail'),
    path('deliveries/<int:pk>/validate/', views.delivery_validate, name='delivery_validate'),

    # Transfers
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfers/new/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('transfers/<int:pk>/validate/', views.transfer_validate, name='transfer_validate'),

    # Adjustments
    path('adjustments/', views.adjustment_list, name='adjustment_list'),
    path('adjustments/new/', views.adjustment_create, name='adjustment_create'),

    # History
    path('history/', views.move_history, name='move_history'),

    # Settings & Profile
    path('settings/', views.settings_view, name='settings'),
    path('profile/', views.profile_view, name='profile'),
]
