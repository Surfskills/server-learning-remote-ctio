# tasks.py
from celery import shared_task
from django.utils import timezone
from .models import Order, Transaction
from .payment_processors import PAYMENT_PROCESSORS

@shared_task
def process_pending_payments():
    pending_orders = Order.objects.filter(status='pending')
    
    for order in pending_orders:
        transaction = order.transactions.filter(type='purchase').first()
        if not transaction:
            continue
            
        processor = PAYMENT_PROCESSORS.get(order.payment_method)
        if not processor:
            continue
            
        result = processor.confirm_payment(transaction.processor_reference)
        if result.get('success') and result.get('status') == 'succeeded':
            order.status = 'paid'
            order.save()