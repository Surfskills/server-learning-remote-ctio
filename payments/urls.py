# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='orders')
router.register(r'payment-methods', views.PaymentMethodViewSet, basename='payment-methods')
router.register(r'refunds', views.RefundViewSet, basename='refunds')
router.register(r'coupons', views.CouponViewSet, basename='coupons')
router.register(r'transactions', views.TransactionViewSet, basename='transactions')

urlpatterns = [
    path('', include(router.urls)),
    path('checkout/', views.CreateOrderView.as_view(), name='create-order'),
    path('invoices/<uuid:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('user-payment-methods/', views.UserPaymentMethodsView.as_view(), name='user-payment-methods'),
    path('validate-coupon/', views.ValidateCouponView.as_view(), name='validate-coupon'),
]