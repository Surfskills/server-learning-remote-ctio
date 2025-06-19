# serializers.py
from rest_framework import serializers
from .models import (
    Order,
    PaymentMethod,
    Refund,
    Coupon,
    OrderItem,
    Invoice,
    Transaction
)
from authentication.serializers import UserSerializer
from courses.serializers import CourseSerializer

class PaymentMethodSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = PaymentMethod
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class CouponSerializer(serializers.ModelSerializer):
    applicable_courses = CourseSerializer(many=True, read_only=True)

    class Meta:
        model = Coupon
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class OrderItemSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    coupon = CouponSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'purchased_at', 'completed_at']

class RefundSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    processed_by = UserSerializer(read_only=True)

    class Meta:
        model = Refund
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'processed_at']

class InvoiceSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'issued_at', 'paid_at']

class TransactionSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'processed_at']

class CreateOrderSerializer(serializers.ModelSerializer):
    payment_method_id = serializers.UUIDField(write_only=True)
    coupon_code = serializers.CharField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Order
        fields = ['course', 'payment_method_id', 'coupon_code']
        extra_kwargs = {
            'course': {'write_only': True},
        }

    def validate(self, data):
        course = data.get('course')
        payment_method_id = data.get('payment_method_id')
        coupon_code = data.get('coupon_code', None)

        # Validate payment method
        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, user=self.context['request'].user)
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Payment method not found")
        
        # Validate coupon if provided
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                if not coupon.is_valid(course):
                    raise serializers.ValidationError("Coupon is not valid for this course")
            except Coupon.DoesNotExist:
                raise serializers.ValidationError("Invalid coupon code")
        
        data['payment_method'] = payment_method
        data['coupon'] = coupon
        return data

    def create(self, validated_data):
        request = self.context['request']
        course = validated_data['course']
        payment_method = validated_data['payment_method']
        coupon = validated_data.get('coupon')

        # Calculate price with discount
        price = course.current_price
        discount = 0
        
        if coupon:
            if coupon.coupon_type == 'percentage':
                discount = price * (coupon.value / 100)
            else:
                discount = coupon.value
            discount = min(discount, price)  # Ensure discount doesn't make price negative
            coupon.uses += 1
            coupon.save()

        # Create order
        order = Order.objects.create(
            user=request.user,
            course=course,
            amount=price - discount,
            payment_method=payment_method.payment_method,
            status='pending'
        )

        # Create order item
        OrderItem.objects.create(
            order=order,
            course=course,
            price=price,
            discount=discount,
            coupon=coupon
        )

        # Create transaction
        Transaction.objects.create(
            order=order,
            user=request.user,
            amount=order.amount,
            type='purchase',
            payment_method=payment_method,
            status='pending'
        )

        return order