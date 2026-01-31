from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import BookingItem, Booking
from .serializers import BookingItemSerializer, BookingSerializer

class CreateBookingItemView(generics.CreateAPIView):
    serializer_class = BookingItemSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UpdateBookingItemView(generics.UpdateAPIView):
    serializer_class = BookingItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BookingItem.objects.filter(user=self.request.user, status='draft')

class BookingItemListView(generics.ListAPIView):
    serializer_class = BookingItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BookingItem.objects.filter(user=self.request.user, status='draft')

class ConfirmBookingView(generics.CreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        draft_items = BookingItem.objects.filter(user=request.user, status='draft')
        
        if not draft_items.exists():
            return Response(
                {'error': 'No draft booking items found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create booking
        booking = Booking.objects.create(
            user=request.user,
            total_amount=sum(item.subtotal for item in draft_items),
            currency='USD'
        )
        
        # Update items
        draft_items.update(booking=booking, status='reserved')
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class BookingListView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

class BookingDetailView(generics.RetrieveAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)