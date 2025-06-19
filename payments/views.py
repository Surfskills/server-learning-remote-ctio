from django.shortcuts import render

# Create your views here.
# views.py
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.db.models import Q
from django.utils import timezone
from core.views import BaseModelViewSet
from core.permissions import IsAdminUser, IsInstructor, IsStudent
from courses.models import Course
from .models import (
    Order,
    PaymentMethod,
    Refund,
    Coupon,
    OrderItem,
    Invoice,
    Transaction
)
from .serializers import (
    OrderSerializer,
    PaymentMethodSerializer,
    RefundSerializer,
    CouponSerializer,
    OrderItemSerializer,
    InvoiceSerializer,
    TransactionSerializer,
    CreateOrderSerializer
)

class OrderViewSet(BaseModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def request_refund(self, request, pk=None):
        order = self.get_object()
        if order.user != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'You do not have permission to request a refund for this order'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status != 'paid':
            return Response(
                {'detail': 'Only paid orders can be refunded'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refund = Refund.objects.create(
            order=order,
            amount=order.amount,
            reason='requested_by_customer',
            status='requested'
        )
        
        return Response(
            {'detail': 'Refund requested successfully', 'refund_id': str(refund.id)},
            status=status.HTTP_201_CREATED
        )

class PaymentMethodViewSet(BaseModelViewSet):
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        payment_method = self.get_object()
        payment_method.is_default = True
        payment_method.save()
        return Response({'detail': 'Payment method set as default'})

class RefundViewSet(BaseModelViewSet):
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Refund.objects.all()
        return Refund.objects.filter(order__user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        refund = self.get_object()
        if refund.status != 'requested':
            return Response(
                {'detail': 'Only requested refunds can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refund.status = 'processing'
        refund.processed_by = request.user
        refund.save()
        
        # Here you would typically call your payment processor's refund API
        # For now, we'll just mark it as completed after a short delay
        refund.status = 'completed'
        refund.save()
        
        return Response({'detail': 'Refund approved and processed'})

class CouponViewSet(BaseModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Coupon.objects.all()

class TransactionViewSet(BaseModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)

class CreateOrderView(generics.CreateAPIView):
    serializer_class = CreateOrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

class InvoiceDetailView(generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    queryset = Invoice.objects.all()

    def get_object(self):
        invoice = super().get_object()
        if invoice.order.user != self.request.user and not self.request.user.is_staff:
            self.permission_denied(self.request)
        return invoice

class UserPaymentMethodsView(generics.ListAPIView):
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user).order_by('-is_default', '-last_used')

class ValidateCouponView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code')
        course_id = request.data.get('course_id')
        
        if not code or not course_id:
            return Response(
                {'detail': 'Both coupon code and course ID are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            coupon = Coupon.objects.get(code=code)
            course = Course.objects.get(id=course_id)
            
            if coupon.is_valid(course):
                discount = 0
                if coupon.coupon_type == 'percentage':
                    discount = course.current_price * (coupon.value / 100)
                else:
                    discount = coupon.value
                
                discount = min(discount, course.current_price)
                
                return Response({
                    'valid': True,
                    'coupon': CouponSerializer(coupon).data,
                    'discount_amount': discount,
                    'final_price': course.current_price - discount
                })
            else:
                return Response({
                    'valid': False,
                    'message': 'Coupon is not valid for this course or has expired'
                })
        except Coupon.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Invalid coupon code'
            })
        except Course.DoesNotExist:
            return Response({
                'detail': 'Course not found'
            }, status=status.HTTP_404_NOT_FOUND)