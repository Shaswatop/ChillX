from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Achievement, UserAchievement, Title, UserTitle
from .serializers import (
    AchievementSerializer, TitleSerializer,
    EquipTitleSerializer, DeductCoinsSerializer,
)


# Works out the tier name from total XP (beginner, gold, etc).
# If removed, tier names and perks stop showing in the UI.
# Called from user_xp_status.
def get_tier_for_xp(xp):
    TIERS = [
        (0, 'beginner'), (1000, 'bronze'), (5000, 'silver'),
        (15000, 'gold'), (35000, 'platinum'), (75000, 'diamond'),
    ]
    tier = TIERS[0][1]
    for min_xp, t in TIERS:
        if xp >= min_xp:
            tier = t
    return tier


# Turns XP into a level number using level ranges.
# If removed, the level shown in the XP widget breaks.
# Called from user_xp_status.
def get_level_from_xp(xp):
    if xp <= 1000:
        return xp // 100 + 1
    if xp <= 3500:
        return 10 + (xp - 1000) // 250 + 1
    if xp <= 8500:
        return 20 + (xp - 3500) // 500 + 1
    if xp <= 28500:
        return 30 + (xp - 8500) // 1000 + 1
    if xp <= 91000:
        return 50 + (xp - 28500) // 2500 + 1
    return 75 + (xp - 91000) // 5000 + 1


# Finds how much XP is needed to reach the next level.
# If removed, progress to next level stops working.
# Called from user_xp_status.
def get_xp_for_level(level):
    if level <= 10:
        return level * 100
    if level <= 20:
        return 1000 + (level - 10) * 250
    if level <= 30:
        return 3500 + (level - 20) * 500
    if level <= 50:
        return 8500 + (level - 30) * 1000
    if level <= 75:
        return 28500 + (level - 50) * 2500
    return 91000 + (level - 75) * 5000


# Returns all achievements for the achievements page.
# If removed, the achievements list loads empty.
# Used by the /api/achievements/ endpoint.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def achievement_list(request):
    qs = Achievement.objects.all()
    serializer = AchievementSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


# Builds the XP status payload (level, tier, buffs, etc).
# If removed, the XP widget on the dashboard breaks.
# Used by the /api/user/xp/ endpoint.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_xp_status(request):
    user = request.user
    level = get_level_from_xp(user.xp)
    tier = get_tier_for_xp(user.xp)
    next_xp = get_xp_for_level(level + 1)
    total_achievements = Achievement.objects.count()
    unlocked_count = UserAchievement.objects.filter(
        user=user, unlocked=True
    ).count()

    return Response({
        'xp': user.xp,
        'level': level,
        'tier': tier,
        'title': user.title or 'The Newcomer',
        'coins': user.coins,
        'diamonds': user.diamonds,
        'xp_to_next': next_xp,
        'total_achievements': total_achievements,
        'unlocked_achievements': unlocked_count,
        'buffs': get_buffs_for_tier(tier),
    })


# Gives the perk list for a tier (xp boost, shop discount).
# If removed, buffs don't show anywhere in the app.
# Called from user_xp_status.
def get_buffs_for_tier(tier):
    buffs_map = {
        'beginner': [
            {'icon': '⚡', 'name': 'XP Multiplier', 'value': '1x', 'color': '#64c864'},
            {'icon': '📋', 'name': 'Daily Challenges', 'value': '3/day', 'color': '#64c864'},
        ],
        'bronze': [
            {'icon': '⚡', 'name': 'XP Multiplier', 'value': '1.1x', 'color': '#cd7f32'},
            {'icon': '📋', 'name': 'Daily Challenges', 'value': '4/day', 'color': '#cd7f32'},
            {'icon': '🏪', 'name': 'Shop Discount', 'value': '5%', 'color': '#cd7f32'},
        ],
        'silver': [
            {'icon': '⚡', 'name': 'XP Multiplier', 'value': '1.2x', 'color': '#c0c0c0'},
            {'icon': '📋', 'name': 'Daily Challenges', 'value': '4/day', 'color': '#c0c0c0'},
            {'icon': '🏪', 'name': 'Shop Discount', 'value': '10%', 'color': '#c0c0c0'},
            {'icon': '🛡️', 'name': 'Streak Shield', 'value': '1/week', 'color': '#c0c0c0'},
        ],
        'gold': [
            {'icon': '⚡', 'name': 'XP Multiplier', 'value': '1.3x', 'color': '#ffd700'},
            {'icon': '📋', 'name': 'Daily Challenges', 'value': '5/day', 'color': '#ffd700'},
            {'icon': '🏪', 'name': 'Shop Discount', 'value': '15%', 'color': '#ffd700'},
            {'icon': '🛡️', 'name': 'Streak Shield', 'value': 'Active', 'color': '#ffd700'},
        ],
        'platinum': [
            {'icon': '⚡', 'name': 'XP Multiplier', 'value': '1.5x', 'color': '#00f5ff'},
            {'icon': '📋', 'name': 'Daily Challenges', 'value': '6/day', 'color': '#00f5ff'},
            {'icon': '🏪', 'name': 'Shop Discount', 'value': '20%', 'color': '#00f5ff'},
            {'icon': '🛡️', 'name': 'Streak Shield', 'value': 'Active', 'color': '#00f5ff'},
        ],
        'diamond': [
            {'icon': '⚡', 'name': 'XP Multiplier', 'value': '2x', 'color': '#9d00ff'},
            {'icon': '📋', 'name': 'Daily Challenges', 'value': '∞', 'color': '#9d00ff'},
            {'icon': '🏪', 'name': 'Shop Discount', 'value': '25%', 'color': '#9d00ff'},
            {'icon': '🛡️', 'name': 'Streak Shield', 'value': 'Active', 'color': '#9d00ff'},
        ],
    }
    if tier in buffs_map:
        return buffs_map[tier]
    return buffs_map['beginner']


# Returns all titles the user can equip.
# If removed, the titles list loads empty.
# Used by the /api/achievements/titles/ endpoint.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def title_list(request):
    qs = Title.objects.all()
    serializer = TitleSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


# Equips a title for the user and unequips all others.
# If removed, equipping titles breaks in the UI.
# Used by the /api/achievements/equip-title/ endpoint.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def equip_title(request):
    serializer = EquipTitleSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    title_id = serializer.validated_data['title_id']
    user = request.user

    try:
        title = Title.objects.get(id=title_id)
    except Title.DoesNotExist:
        return Response({'error': 'Title not found'}, status=status.HTTP_404_NOT_FOUND)

    ut, created = UserTitle.objects.get_or_create(user=user, title=title)
    if not ut.unlocked and user.xp < title.min_xp:
        return Response({'error': 'Title not yet unlocked'}, status=status.HTTP_400_BAD_REQUEST)

    if not ut.unlocked:
        ut.unlocked = True
        ut.save()

    UserTitle.objects.filter(user=user, equipped=True).update(equipped=False)
    ut.equipped = True
    ut.save()

    user.title = title.name
    user.save(update_fields=['title'])

    return Response({'success': True, 'title': title.name})


# Adds progress to an achievement and unlocks it when done.
# If removed, achievements never track progress or give rewards.
# Used by the /api/achievements/progress/ endpoint.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_achievement_progress(request):
    achievement_id = request.data.get('achievement_id')
    increment = request.data.get('increment', 1)

    if not achievement_id:
        return Response({'error': 'achievement_id required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        achievement = Achievement.objects.get(id=achievement_id)
    except Achievement.DoesNotExist:
        return Response({'error': 'Achievement not found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    ua, created = UserAchievement.objects.get_or_create(user=user, achievement=achievement)

    if ua.unlocked:
        return Response({'error': 'Already unlocked'}, status=status.HTTP_400_BAD_REQUEST)

    ua.progress += increment
    if ua.progress >= achievement.max_progress:
        ua.unlocked = True
        ua.unlocked_at = timezone.now()
        user.xp += achievement.xp_reward
        user.coins += achievement.coin_reward
        user.save(update_fields=['xp', 'coins'])

    ua.save()

    xp_gained = 0
    coins_gained = 0
    if ua.unlocked:
        xp_gained = achievement.xp_reward
        coins_gained = achievement.coin_reward

    return Response({
        'progress': ua.progress,
        'unlocked': ua.unlocked,
        'xp_gained': xp_gained,
        'coins_gained': coins_gained,
    })


# Takes coins from the user if they have enough.
# If removed, buying anything in the shop breaks.
# Used by the /api/user/deduct-coins/ endpoint.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deduct_coins(request):
    serializer = DeductCoinsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    amount = serializer.validated_data['amount']

    if user.coins < amount:
        return Response({'error': 'Not enough coins'}, status=status.HTTP_400_BAD_REQUEST)

    user.coins -= amount
    user.save(update_fields=['coins'])

    return Response({'success': True, 'coins_left': user.coins})
