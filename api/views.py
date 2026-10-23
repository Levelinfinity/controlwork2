from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Room, Booking, UserProfile
from .serializers import RoomSerializer, BookingSerializer, UserProfileSerializer

# Create your views here.

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title']
    filterset_fields = ['capacity', 'is_active']
    ordering_fields = ['price_per_hour', 'capacity']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def list(self, request, *args, **kwargs):
        cached_rooms = cache.get('room_list_data')
        if not cached_rooms:
            response = super().list(request, *args, **kwargs)
            cache.set('room_list_data', response.data, 60)
            return response
        return Response(cached_rooms)

    def perform_create(self, serializer):
        serializer.save()
        cache.delete('room_list_data')

    def perform_update(self, serializer):
        serializer.save()
        cache.delete('room_list_data')

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        if room.bookings.exists():
            return Response(
                {"error": "Нельзя удалить комнату, у которой уже есть бронирования."},
                status=status.HTTP_400_BAD_REQUEST
            )
        cache.delete('room_list_data')
        return super().destroy(request, *args, **kwargs)


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'start_time']

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related('room', 'user')

    def perform_create(self, serializer):
        total_price = serializer.validated_data.pop('calculated_total_price')
        
        profile = self.request.user.profile
        profile.balance -= total_price
        profile.save()

        serializer.save(user=self.request.user, total_price=total_price) 