# admin.py
from django.contrib import admin
from .models import (
    Order,
    PaymentMethod,
    Refund,
    Coupon,
    OrderItem,
    Invoice,
    Transaction
)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'amount', 'status', 'purchased_at')
    list_filter = ('status', 'payment_method', 'purchased_at')
    search_fields = ('user__email', 'course__title', 'transaction_id')
    readonly_fields = ('purchased_at', 'completed_at')
    date_hierarchy = 'purchased_at'

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'is_default', 'last_used')
    list_filter = ('type', 'is_default')
    search_fields = ('user__email',)
    readonly_fields = ('last_used',)

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'status', 'reason', 'processed_at')
    list_filter = ('status', 'reason')
    search_fields = ('order__id', 'notes')
    readonly_fields = ('processed_at',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'coupon_type', 'value', 'uses', 'max_uses', 'active')
    list_filter = ('coupon_type', 'active')
    search_fields = ('code', 'description')
    filter_horizontal = ('applicable_courses',)
    readonly_fields = ('uses',)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'course', 'price', 'discount', 'final_price')
    list_filter = ('course',)
    search_fields = ('order__id', 'course__title')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'order', 'total', 'issued_at', 'paid_at')
    list_filter = ('issued_at', 'paid_at')
    search_fields = ('invoice_number', 'order__id')
    readonly_fields = ('invoice_number', 'issued_at', 'paid_at')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'type', 'status', 'processed_at')
    list_filter = ('type', 'status', 'currency')
    search_fields = ('user__email', 'order__id')
    readonly_fields = ('processed_at',)