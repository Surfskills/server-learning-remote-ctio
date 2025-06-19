# payment_processors.py
from django.conf import settings
import stripe
import logging

logger = logging.getLogger(__name__)

class StripeProcessor:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_payment_intent(self, amount, currency='usd', metadata=None):
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                metadata=metadata or {}
            )
            return {
                'success': True,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def confirm_payment(self, payment_intent_id):
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if intent.status == 'succeeded':
                return {
                    'success': True,
                    'status': 'succeeded',
                    'payment_intent': intent
                }
            return {
                'success': True,
                'status': intent.status,
                'payment_intent': intent
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class PayPalProcessor:
    # Implement PayPal integration similarly
    pass

PAYMENT_PROCESSORS = {
    'stripe': StripeProcessor(),
    'paypal': PayPalProcessor()
}