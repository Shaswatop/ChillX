from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone
from .models import ShopItem, UserInventory, Purchase, Raffle, RaffleTicket, Achievement, UserAchievement, Title, UserTitle


class ShopItemSerializer(serializers.ModelSerializer):
    sale_price = serializers.IntegerField(read_only=True)
    owned = serializers.SerializerMethodField()

    class Meta:
        model = ShopItem
        fields = '__all__'

    def get_owned(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return UserInventory.objects.filter(user=user, item=obj).exists()
        return False


class PurchaseSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    currency = serializers.CharField(default='coins', required=False)

    def validate(self, data):
        user = self.context['request'].user
        try:
            item = ShopItem.objects.get(id=data['item_id'])
        except ShopItem.DoesNotExist:
            raise serializers.ValidationError('Item not found.')
        if UserInventory.objects.filter(user=user, item=item).exists():
            raise serializers.ValidationError('Already owned.')
        currency = data.get('currency', 'coins')
        if currency == 'gems':
            if user.diamonds < item.price_gems:
                raise serializers.ValidationError(f'Need {item.price_gems - user.diamonds} more gems.')
        else:
            if user.coins < item.sale_price:
                raise serializers.ValidationError(f'Need {item.sale_price - user.coins} more coins.')
        if item.is_limited and item.stock_remaining <= 0:
            raise serializers.ValidationError('Out of stock.')
        data['item'] = item
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        item = self.validated_data['item']
        currency = self.validated_data.get('currency', 'coins')
        if currency == 'gems':
            price = item.price_gems
            user.diamonds -= price
        else:
            price = item.sale_price
            user.coins -= price
        if item.name == 'AI Profile Pic Generator':
            user.profile_pic_generations += 3
            user.save(update_fields=['coins', 'profile_pic_generations', 'diamonds'])
        else:
            user.save(update_fields=['coins', 'diamonds'])
            UserInventory.objects.create(user=user, item=item)
        Purchase.objects.create(user=user, item=item, coins_spent=price if currency != 'gems' else 0)
        if item.is_limited and item.stock_remaining > 0:
            item.stock_remaining -= 1
            item.save(update_fields=['stock_remaining'])
        return item


class RaffleSerializer(serializers.ModelSerializer):
    total_tickets_sold = serializers.SerializerMethodField()
    user_tickets = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Raffle
        fields = '__all__'

    def get_total_tickets_sold(self, obj):
        total = RaffleTicket.objects.filter(raffle=obj).aggregate(Sum('quantity'))
        return total['quantity__sum'] or 0

    def get_user_tickets(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            tickets = RaffleTicket.objects.filter(raffle=obj, user=user).aggregate(Sum('quantity'))
            return tickets['quantity__sum'] or 0
        return 0

    def get_time_remaining(self, obj):
        remaining = obj.ends_at - timezone.now()
        return max(0, int(remaining.total_seconds()))


class RaffleBuySerializer(serializers.Serializer):
    raffle_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=10)

    def validate(self, data):
        user = self.context['request'].user
        try:
            raffle = Raffle.objects.get(id=data['raffle_id'], is_active=True)
        except Raffle.DoesNotExist:
            raise serializers.ValidationError('Raffle not found.')
        tickets_owned = RaffleTicket.objects.filter(raffle=raffle, user=user).aggregate(Sum('quantity'))
        current = tickets_owned['quantity__sum'] or 0
        if current + data['quantity'] > raffle.max_tickets_per_user:
            raise serializers.ValidationError(f'Max {raffle.max_tickets_per_user} tickets per user.')
        total_cost = data['quantity'] * raffle.ticket_price
        if user.coins < total_cost:
            raise serializers.ValidationError(f'Need {total_cost - user.coins} more coins.')
        data['raffle'] = raffle
        data['total_cost'] = total_cost
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        raffle = self.validated_data['raffle']
        qty = self.validated_data['quantity']
        cost = self.validated_data['total_cost']
        user.coins -= cost
        user.save(update_fields=['coins'])
        RaffleTicket.objects.create(user=user, raffle=raffle, quantity=qty)
        return raffle


# ── ACHIEVEMENT SERIALIZERS ──

class AchievementSerializer(serializers.ModelSerializer):
    unlocked = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    unlocked_at = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = '__all__'

    def get_unlocked(self, obj):
        user = self.context['request'].user
        try:
            ua = UserAchievement.objects.get(user=user, achievement=obj)
            return ua.unlocked or ua.progress >= obj.max_progress
        except UserAchievement.DoesNotExist:
            return obj.max_progress <= 0

    def get_progress(self, obj):
        user = self.context['request'].user
        try:
            ua = UserAchievement.objects.get(user=user, achievement=obj)
            return ua.progress
        except UserAchievement.DoesNotExist:
            return 0

    def get_unlocked_at(self, obj):
        user = self.context['request'].user
        try:
            ua = UserAchievement.objects.get(user=user, achievement=obj)
            return ua.unlocked_at.isoformat() if ua.unlocked_at else None
        except UserAchievement.DoesNotExist:
            return None


class TitleSerializer(serializers.ModelSerializer):
    unlocked = serializers.SerializerMethodField()
    equipped = serializers.SerializerMethodField()

    class Meta:
        model = Title
        fields = '__all__'

    def get_unlocked(self, obj):
        user = self.context['request'].user
        try:
            ut = UserTitle.objects.get(user=user, title=obj)
            return ut.unlocked
        except UserTitle.DoesNotExist:
            return user.xp >= obj.min_xp

    def get_equipped(self, obj):
        user = self.context['request'].user
        try:
            ut = UserTitle.objects.get(user=user, title=obj)
            return ut.equipped
        except UserTitle.DoesNotExist:
            return False


class EquipTitleSerializer(serializers.Serializer):
    title_id = serializers.IntegerField()

    def validate_title_id(self, value):
        try:
            Title.objects.get(id=value)
        except Title.DoesNotExist:
            raise serializers.ValidationError('Title not found')
        return value


class DeductCoinsSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=255, required=False, default='')
