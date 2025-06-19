# models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.models import BaseModel
from authentication.models import User
from courses.models import Course

class Order(BaseModel):
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('mpesa', 'M-Pesa'),
        ('crypto', 'Cryptocurrency'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='orders')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_details = models.JSONField(default=dict, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-purchased_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['purchased_at']),
            models.Index(fields=['user', 'course']),
        ]

    def __str__(self):
        return f"Order #{self.id} for {self.user.email}"

    def save(self, *args, **kwargs):
        if self.status == 'paid' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

class PaymentMethod(BaseModel):
    PAYMENT_TYPE_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('wallet', 'Digital Wallet'),
        ('bank', 'Bank Account'),
        ('mobile', 'Mobile Money'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    is_default = models.BooleanField(default=False)
    details = models.JSONField(default=dict)
    last_used = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-is_default', '-last_used']
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"

    def __str__(self):
        return f"{self.get_type_display()} for {self.user.email}"

    def save(self, *args, **kwargs):
        # Ensure only one default payment method per user
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

class Refund(BaseModel):
    REFUND_STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('denied', 'Denied'),
    ]
    
    REASON_CHOICES = [
        ('duplicate', 'Duplicate charge'),
        ('fraudulent', 'Fraudulent'),
        ('requested_by_customer', 'Requested by customer'),
        ('product_unsatisfactory', 'Product unsatisfactory'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='requested')
    notes = models.TextField(blank=True, null=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='processed_refunds')
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund for Order #{self.order.id}"

    def clean(self):
        if self.amount > self.order.amount:
            raise ValidationError("Refund amount cannot exceed order amount")

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)

class Coupon(BaseModel):
    COUPON_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    max_uses = models.PositiveIntegerField(default=1)
    uses = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    applicable_courses = models.ManyToManyField(Course, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Coupon {self.code}"

    def is_valid(self, course=None):
        now = timezone.now()
        return (
            self.active and
            self.uses < self.max_uses and
            self.valid_from <= now <= self.valid_to and
            (not course or self.applicable_courses.filter(id=course.id).exists())
        )

class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.course.title} in Order #{self.order.id}"

    @property
    def final_price(self):
        return self.price - self.discount

class Invoice(BaseModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=20, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField()
    paid_at = models.DateTimeField(blank=True, null=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    pdf = models.FileField(upload_to='invoices/', blank=True, null=True)

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number (you might want a better system)
            last_invoice = Invoice.objects.order_by('-id').first()
            last_num = int(last_invoice.invoice_number.split('-')[1]) if last_invoice else 0
            self.invoice_number = f"INV-{last_num + 1:06d}"
        
        if not self.due_at:
            self.due_at = self.issued_at + timedelta(days=14)
            
        super().save(*args, **kwargs)

class Transaction(BaseModel):
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    TRANSACTION_TYPE_CHOICES = [
        ('purchase', 'Purchase'),
        ('refund', 'Refund'),
        ('withdrawal', 'Withdrawal'),
        ('deposit', 'Deposit'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True, related_name='transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, blank=True, null=True)
    processor_response = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} of {self.amount} {self.currency} for {self.user.email}"

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)