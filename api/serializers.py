from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone
from .models import Room, UserProfile, Booking

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'phone_number', 'balance']
        read_only_fields = ['balance']


class BookingSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'user', 'room', 'start_time', 'end_time', 'total_price', 'status', 'created_at']
        read_only_fields = ['user', 'total_price', 'status', 'created_at']

    def validate(self, attrs):
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        room = attrs.get('room')
        user = self.context['request'].user

        if start_time < timezone.now():
            raise serializers.ValidationError("Нельзя бронировать на прошедшее время.")

        if end_time <= start_time:
            raise serializers.ValidationError("Время окончания должно быть позже времени начала.")

        duration = (end_time - start_time).total_seconds() / 3600
        if duration < 1 or duration > 12:
            raise serializers.ValidationError("Продолжительность бронирования должна быть от 1 до 12 часов.")

        if not room.is_active:
            raise serializers.ValidationError("Эта комната недоступна для бронирования.")

        total_price = room.price_per_hour * Decimal(str(duration))
        if user.profile.balance < total_price:
            raise serializers.ValidationError(
                f"Недостаточно средств. Требуется: {total_price}, Ваш баланс: {user.profile.balance}"
            )

        overlapping_bookings = Booking.objects.filter(
            room=room,
            status__in=['pending', 'confirmed'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        if self.instance:
            overlapping_bookings = overlapping_bookings.exclude(pk=self.instance.pk)

        if overlapping_bookings.exists():
            raise serializers.ValidationError("Комната уже забронирована на выбранный временной интервал.")

        attrs['calculated_total_price'] = total_price
        return attrs