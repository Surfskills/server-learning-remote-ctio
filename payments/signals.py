# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, Invoice
from django.utils import timezone
from datetime import timedelta

@receiver(post_save, sender=Order)
def create_invoice_for_order(sender, instance, created, **kwargs):
    if created:
        Invoice.objects.create(
            order=instance,
            subtotal=instance.amount,
            tax_amount=0,  # You might calculate this based on your requirements
            total=instance.amount,
            due_at=timezone.now() + timedelta(days=14)
        )

@receiver(post_save, sender=Order)
def update_transaction_status(sender, instance, **kwargs):
    if instance.status == 'paid':
        transaction = instance.transactions.filter(type='purchase').first()
        if transaction and transaction.status != 'completed':
            transaction.status = 'completed'
            transaction.processed_at = timezone.now()
            transaction.save()