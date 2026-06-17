import random
import base64
import io
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import ShopItem, UserInventory, Purchase, Raffle
from .serializers import (
    ShopItemSerializer, PurchaseSerializer,
    RaffleSerializer, RaffleBuySerializer,
)
from .ai_service import _gemini_request, _gemini_image_generate, _gemini_text_to_image


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shop_items(request):
    category = request.GET.get('category')
    rarity = request.GET.get('rarity')
    qs = ShopItem.objects.all()
    if category:
        qs = qs.filter(category=category)
    if rarity:
        qs = qs.filter(rarity=rarity)
    serializer = ShopItemSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shop_featured(request):
    qs = ShopItem.objects.filter(is_featured=True)[:3]
    serializer = ShopItemSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def shop_buy(request):
    serializer = PurchaseSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        item = serializer.save()
        currency = request.data.get('currency', 'coins')
        if currency == 'gems':
            return Response({'success': True, 'item': item.name, 'gems_left': request.user.diamonds})
        return Response({'success': True, 'item': item.name, 'coins_left': request.user.coins})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shop_inventory(request):
    items = UserInventory.objects.filter(user=request.user)
    data = [{
        'id': inv.id,
        'item_id': inv.item.id,
        'name': inv.item.name,
        'description': inv.item.description,
        'icon': inv.item.icon,
        'rarity': inv.item.rarity,
        'category': inv.item.category,
        'is_active': inv.is_active,
        'purchased_at': inv.purchased_at.isoformat(),
        'expires_at': inv.expires_at.isoformat() if inv.expires_at else None,
    } for inv in items]
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def inventory_toggle(request):
    inv_id = request.data.get('inventory_id')
    if not inv_id:
        return Response({'error': 'inventory_id required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        inv = UserInventory.objects.get(id=inv_id, user=request.user)
    except UserInventory.DoesNotExist:
        return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)

    EFFECT_MAP = {
        'Animated Rainbow Name': 'rainbow-name',
        'Gold Username': 'gold-name',
        'Flame Profile Border': 'flame-border',
        'Electric Profile Border': 'electric-border',
        'Shooting Star Effect': 'shooting-stars',
        'Blood Moon Effect': 'blood-moon',
        'Void Effect': 'void',
        'Holographic Name': 'holo',
        'Matrix Rain': 'matrix',
        'Angel Effect': 'angel',
        'Demon Effect': 'demon',
        'Galaxy Effect': 'galaxy',
        'Neon Sign': 'neon',
        'Cyberpunk Effect': 'cyber',
        'Sakura Effect': 'sakura',
        'Lava Effect': 'lava',
        'Shadow Effect': 'shadow',
        'Thunder Effect': 'thunder',
        'Saturn Ring': 'ring',
        'Cursed Effect': 'cursed',
        'Crypto Ticker': 'crypto',
        'Pixel Name': 'pixel',
        'Dragon Effect': 'dragon',
        'Sunrise Effect': 'sunrise',
        'Overloaded Effect': 'overload',
        'Bounty Hunter': 'bounty',
        'Frostbite Effect': 'frost',
        'Nepal Name': 'nepal',
        'Toxic Name': 'toxic',
        'Ice Border': 'ice',
        'Glitch Name': 'glitch',
        'Sakura Storm': 'sakura-storm',
        'Ocean Depths': 'ocean-depths',
        'Sunset Horizon': 'sunset-horizon',
        'Cosmic Nebula': 'cosmic-nebula',
        'Neon Grid': 'neon-grid',
        'Starry Sky': 'starry-sky',
        'Lava Flow': 'lava-flow',
        'Crystal Aura': 'crystal-aura',
        'Frostwind': 'frostwind',
        'Thunder Storm': 'thunder-storm',
        'Fire Spirit': 'fire-spirit',
        'Mystic Mist': 'mystic-mist',
        'Stardust Burst': 'stardust',
        'Ember Sparks': 'ember-sparks',
        'Snowfall': 'snowfall',
        'Energy Arc': 'energy-arc',
        'Neon Rain': 'neon-rain',
        'Spirit Orbs': 'spirit-orbs',
    }

    NAME_EFFECTS = {
        'rainbow-name', 'gold-name', 'matrix', 'neon', 'cyber', 'pixel',
        'crypto', 'bounty', 'nepal', 'toxic', 'glitch', 'cursed', 'shadow',
        'holo', 'sakura', 'galaxy', 'ring',
    }
    BORDER_EFFECTS = {
        'flame-border', 'electric-border', 'ice', 'frost', 'blood-moon',
        'void', 'lava', 'dragon', 'sunrise', 'overload', 'thunder',
    }
    AVATAR_EFFECTS = {
        'shooting-stars', 'angel', 'demon',
        'sakura-storm', 'ocean-depths', 'sunset-horizon', 'cosmic-nebula',
        'neon-grid', 'starry-sky', 'lava-flow', 'crystal-aura',
        'frostwind', 'thunder-storm', 'fire-spirit', 'mystic-mist',
        'stardust', 'ember-sparks', 'snowfall', 'energy-arc',
        'neon-rain', 'spirit-orbs',
    }

    name = inv.item.name
    slot = None
    effect_key = None

    if inv.item.category == 'flex':
        if name.startswith('Title:') or name == 'Custom Title' or name in ('Global Shoutout 24hr', 'Leaderboard Pin 24hr'):
            slot = 'title'
        elif name in EFFECT_MAP:
            effect_key = EFFECT_MAP[name]
            if effect_key in NAME_EFFECTS:
                slot = 'name'
            elif effect_key in BORDER_EFFECTS:
                slot = 'border'
            elif effect_key in AVATAR_EFFECTS:
                slot = 'avatar'
            else:
                slot = 'bg'
        else:
            slot = 'title'
    else:
        inv.is_active = not inv.is_active
        inv.save(update_fields=['is_active'])
        return Response({'is_active': inv.is_active})

    if slot:
        if inv.is_active:
            inv.is_active = False
            inv.save(update_fields=['is_active'])
            if slot == 'title':
                request.user.title = ''
                request.user.flex_effect = ''
            elif slot == 'name':
                request.user.name_effect = ''
            elif slot == 'border':
                request.user.avatar_border = ''
            elif slot == 'avatar':
                request.user.bg_effect = ''
            elif slot == 'bg':
                request.user.bg_effect = ''
            request.user.save(update_fields=['title', 'flex_effect', 'name_effect', 'avatar_border', 'bg_effect'])
        else:
            same_slot_items = UserInventory.objects.filter(
                user=request.user, item__category='flex', is_active=True
            )
            for other in same_slot_items:
                other_name = other.item.name
                other_key = EFFECT_MAP.get(other_name, '')
                other_slot = None
                if other_name.startswith('Title:') or other_name == 'Custom Title' or other_name in ('Global Shoutout 24hr', 'Leaderboard Pin 24hr'):
                    other_slot = 'title'
                elif other_key in NAME_EFFECTS:
                    other_slot = 'name'
                elif other_key in BORDER_EFFECTS:
                    other_slot = 'border'
                elif other_key in AVATAR_EFFECTS:
                    other_slot = 'avatar'
                else:
                    other_slot = 'bg'
                if other_slot == slot:
                    other.is_active = False
                    other.save(update_fields=['is_active'])

            inv.is_active = True
            inv.save(update_fields=['is_active'])

            if slot == 'title':
                if name.startswith('Title:'):
                    request.user.title = name.replace('Title: ', '')
                elif name == 'Custom Title':
                    request.user.title = request.user.custom_title or 'Custom'
                elif name == 'Global Shoutout 24hr':
                    request.user.title = '⭐ Global Shoutout ⭐'
                elif name == 'Leaderboard Pin 24hr':
                    request.user.title = '📌 Pinned'
                else:
                    request.user.title = name
                request.user.flex_effect = 'title'
                request.user.save(update_fields=['title', 'flex_effect'])
            elif slot == 'name':
                request.user.name_effect = effect_key
                request.user.save(update_fields=['name_effect'])
            elif slot == 'border':
                request.user.avatar_border = effect_key
                request.user.save(update_fields=['avatar_border'])
            elif slot == 'avatar':
                request.user.bg_effect = effect_key
                request.user.save(update_fields=['bg_effect'])

    return Response({'is_active': inv.is_active})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crate_open(request):
    try:
        inv_id = request.data.get('inventory_id')
        item_id = request.data.get('item_id')
        if inv_id:
            try:
                inv = UserInventory.objects.get(id=inv_id, user=request.user)
            except UserInventory.DoesNotExist:
                return Response({'error': 'Crate not found'}, status=status.HTTP_404_NOT_FOUND)
        elif item_id:
            inv = UserInventory.objects.filter(user=request.user, item_id=item_id, item__category='lootbox').first()
            if not inv:
                return Response({'error': 'Crate not found in inventory'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'inventory_id or item_id required'}, status=status.HTTP_400_BAD_REQUEST)

        if inv.item.category != 'lootbox':
            return Response({'error': 'Not a crate'}, status=status.HTTP_400_BAD_REQUEST)

        rarity_weights = {'common': 50, 'rare': 30, 'epic': 15, 'legendary': 5}
        if 'Epic' in inv.item.name:
            rarity_weights = {'common': 0, 'rare': 20, 'epic': 50, 'legendary': 30}
        if 'Legendary' in inv.item.name:
            rarity_weights = {'common': 0, 'rare': 10, 'epic': 40, 'legendary': 50}
        if 'Mystery' in inv.item.name:
            rarity_weights = {'common': 30, 'rare': 30, 'epic': 28, 'legendary': 12}

        rarities = list(rarity_weights.keys())
        weights = list(rarity_weights.values())
        chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]

        pool = list(ShopItem.objects.filter(category__in=['boosts', 'flex', 'cosmetics'], rarity=chosen_rarity).exclude(
            id__in=UserInventory.objects.filter(user=request.user).values('item_id')
        ))
        if not pool:
            pool = list(ShopItem.objects.filter(category__in=['boosts', 'flex', 'cosmetics'], rarity=chosen_rarity))

        if not pool:
            pool = list(ShopItem.objects.filter(rarity=chosen_rarity).exclude(category='lootbox'))

        if not pool:
            return Response({'error': 'No rewards available right now'}, status=status.HTTP_400_BAD_REQUEST)

        reward = random.choice(pool)
        UserInventory.objects.get_or_create(user=request.user, item=reward)
        inv.delete()

        return Response({
            'rarity': chosen_rarity,
            'item': {'id': reward.id, 'name': reward.name, 'icon': reward.icon, 'rarity': reward.rarity, 'description': reward.description},
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def avatar_upload(request):
    user = request.user
    image_data = request.data.get('image')
    if not image_data:
        return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        img_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(img_bytes)).convert('RGBA')
        img = img.resize((512, 512), Image.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format='PNG')
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        user.avatar_base64 = img_base64
        user.save(update_fields=['avatar_base64'])
        return Response({'image': img_base64, 'message': 'Avatar updated!'})
    except Exception as e:
        return Response({'error': f'Upload failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


AI_STYLE_COST = 500
AI_ANIMATE_COST = 300
AI_STYLES = ['anime', 'neon', 'vintage', 'glitch', 'oil', 'pop-art', 'cyberpunk', 'watercolor']


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_profile_pic(request):
    user = request.user
    image_data = request.data.get('image')
    style = request.data.get('style', 'anime')
    prompt = request.data.get('prompt', '')
    animate = request.data.get('animate', False)
    text_only = request.data.get('text_only', False)

    if style not in AI_STYLES:
        return Response({'error': f'Invalid style. Choose from: {", ".join(AI_STYLES)}'}, status=status.HTTP_400_BAD_REQUEST)

    total_cost = AI_STYLE_COST + (AI_ANIMATE_COST if animate else 0)
    if user.coins < total_cost:
        return Response({'error': f'Need {total_cost} coins (have {user.coins})'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        style_prompts = {
            'anime': 'Transform this photo into high-quality Japanese anime art style. Make it look like a professional anime character portrait with clean cel-shaded colors, large expressive eyes, soft skin shading, vibrant saturated colors, and anime aesthetic. Keep the person recognizable but fully redrawn in anime style.',
            'neon': 'Transform this photo into a glowing neon cyberpunk portrait. Add bright neon lights in cyan, magenta, and purple. Dark background with colorful neon reflections on face and clothes. Vivid glowing neon colors, high contrast.',
            'vintage': 'Transform this photo into a beautiful vintage retro portrait. Warm sepia tones, soft film grain, faded colors, slight vignette, nostalgic 1970s film photography look.',
            'glitch': 'Transform this photo into digital glitch art. Add RGB channel splitting, scanlines, pixel displacement, and colorful data corruption artifacts. Broken digital screen aesthetic.',
            'oil': 'Transform this photo into a stunning oil painting. Thick visible brushstrokes, rich saturated colors, impasto texture, like a classical Impressionist painting on canvas.',
            'pop-art': 'Transform this photo into bold Andy Warhol pop art. Flat bright colors, halftone dot patterns, thick black outlines, comic book aesthetic, screen print look.',
            'cyberpunk': 'Transform this photo into a cyberpunk character portrait. Dark moody background, cyan and magenta neon rim lighting, futuristic elements, digital rain in background, noir feel.',
            'watercolor': 'Transform this photo into a beautiful watercolor painting. Soft translucent colors bleeding into each other, wet edges, paper texture visible, gentle artistic feel.',
        }

        style_prompts_txt = {
            'anime': 'A beautiful high-quality Japanese anime character portrait of a young person, cel-shaded colors, large expressive eyes, soft skin shading, vibrant colors, anime aesthetic, clean linework.',
            'neon': 'A glowing neon cyberpunk portrait of a person, bright neon cyan magenta and purple lights, dark background with colorful neon reflections on face, vivid glowing colors, high contrast.',
            'vintage': 'A beautiful vintage retro portrait of a person, warm sepia tones, soft film grain, faded colors, slight vignette, nostalgic 1970s film photography look.',
            'glitch': 'Digital glitch art portrait of a person, RGB channel splitting, scanlines, pixel displacement, colorful data corruption artifacts, broken digital screen aesthetic.',
            'oil': 'A stunning oil painting portrait of a person, thick visible brushstrokes, rich saturated colors, impasto texture, classical Impressionist painting on canvas.',
            'pop-art': 'Bold Andy Warhol pop art portrait of a person, flat bright colors, halftone dot patterns, thick black outlines, comic book aesthetic, screen print look.',
            'cyberpunk': 'Cyberpunk character portrait of a person, dark moody background, cyan and magenta neon rim lighting, futuristic elements, digital rain in background, noir feel.',
            'watercolor': 'A beautiful watercolor painting portrait of a person, soft translucent colors bleeding into each other, wet edges, paper texture visible, gentle artistic feel.',
        }

        if text_only or not image_data:
            gen_prompt = style_prompts_txt.get(style, f'Create an image in {style} artistic style.')
            if prompt:
                gen_prompt = f'{prompt}. Style: {style}. {gen_prompt}'
            img_result = _gemini_text_to_image(gen_prompt)
            used_gemini = img_result and isinstance(img_result, str) and len(img_result) > 100
            if not used_gemini:
                return Response({'error': 'Image generation failed. The free API tier is rate-limited. Try uploading a photo instead.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            img_base64 = img_result
        else:
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            raw_b64 = image_data

            gen_prompt = style_prompts.get(style, f'Transform this photo into {style} artistic style.')
            if prompt:
                gen_prompt += f' Additional instructions: {prompt}'
            gen_prompt += ' Output only the transformed image with no text or labels.'

            img_result = _gemini_image_generate(raw_b64, gen_prompt)
            used_gemini = img_result and isinstance(img_result, str) and len(img_result) > 100

            if not used_gemini:
                return Response({'error': 'AI transformation unavailable (API rate limit). Try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            img_base64 = img_result

        if animate and used_gemini:
            img_bytes = base64.b64decode(img_base64)
            src_img = Image.open(io.BytesIO(img_bytes)).convert('RGBA').resize((512, 512), Image.LANCZOS)
            frames = []
            for i in range(8):
                frame = src_img.copy()
                r, g, b, a = frame.split()
                shift = (i / 8.0)
                r = r.point(lambda x: min(255, int(x + shift * 30)))
                g = g.point(lambda x: min(255, int(x - shift * 15)))
                b = b.point(lambda x: min(255, int(x + shift * 20)))
                frame = Image.merge('RGBA', (r, g, b, a))
                enhancer = ImageEnhance.Brightness(frame)
                frame = enhancer.enhance(1.0 + shift * 0.1)
                frames.append(frame.convert('RGB'))
            gif_buffer = io.BytesIO()
            frames[0].save(gif_buffer, format='GIF', save_all=True, append_images=frames[1:], duration=120, loop=0, optimize=False)
            gif_buffer.seek(0)
            img_base64 = base64.b64encode(gif_buffer.read()).decode()

        user.coins -= total_cost
        user.save(update_fields=['coins'])

        method_label = 'AI' if used_gemini else 'Local'
        return Response({
            'image': img_base64 if not animate else (img_base64 if not animate else img_base64),
            'image_animated': img_base64 if animate else None,
            'coins_left': user.coins,
            'cost': total_cost,
            'style': style,
            'animated': animate,
            'ai_caption': f'{method_label} {style.title()}',
            'ai_params': {'method': method_label, 'animated': animate, 'frames': 8 if animate else 1},
        })
    except Exception as e:
        return Response({'error': f'Image generation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shop_wallet(request):
    u = request.user
    return Response({
        'coins': u.coins,
        'gems': u.diamonds,
        'profile_pic_generations': u.profile_pic_generations,
        'name_effect': u.name_effect,
        'avatar_border': u.avatar_border,
        'bg_effect': u.bg_effect,
        'flex_effect': u.flex_effect,
        'title': u.title,
        'has_avatar': bool(u.avatar_base64),
        'display_name': u.display_name or u.username,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avatar_image(request):
    user_id = request.GET.get('user_id')
    if user_id:
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()
        try:
            u = UserModel.objects.get(id=user_id)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
    else:
        u = request.user
    if not u.avatar_base64:
        return Response({'error': 'No avatar'}, status=404)
    from django.http import HttpResponse
    import base64 as b64
    import re
    try:
        raw = u.avatar_base64
        if ',' in raw:
            raw = raw.split(',')[1]
        img_data = b64.b64decode(raw)
        content_type = 'image/png'
        if img_data[:3] == b'GIF':
            content_type = 'image/gif'
        resp = HttpResponse(img_data, content_type=content_type)
        resp['Cache-Control'] = 'private, max-age=0, must-revalidate'
        resp['Pragma'] = 'no-cache'
        return resp
    except Exception:
        return Response({'error': 'Invalid avatar'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def raffle_current(request):
    raffle = Raffle.objects.filter(is_active=True, ends_at__gt=timezone.now()).first()
    if not raffle:
        return Response({'active': False})
    serializer = RaffleSerializer(raffle, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def raffle_buy(request):
    serializer = RaffleBuySerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({'success': True, 'coins_left': request.user.coins})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def custom_title_create(request):
    title_text = request.data.get('title', '').strip()
    if not title_text or len(title_text) > 30:
        return Response({'error': 'Title must be 1-30 characters.'}, status=status.HTTP_400_BAD_REQUEST)

    cost = 2000
    user = request.user
    if user.coins < cost:
        return Response({'error': f'Need {cost - user.coins} more coins.'}, status=status.HTTP_400_BAD_REQUEST)

    title_item, _ = ShopItem.objects.get_or_create(name='Custom Title', defaults={
        'description': 'Your custom title',
        'category': 'flex', 'rarity': 'legendary',
        'price_coins': cost, 'icon': '✏️',
    })

    user.coins -= cost
    user.custom_title = title_text
    user.save(update_fields=['coins', 'custom_title'])

    inv, created = UserInventory.objects.get_or_create(user=user, item=title_item, defaults={'is_active': False})
    if not created:
        inv.is_active = False
        inv.save(update_fields=['is_active'])

    # Deactivate other flex, activate this one
    UserInventory.objects.filter(user=user, item__category='flex', is_active=True).exclude(id=inv.id).update(is_active=False)
    inv.is_active = True
    inv.save(update_fields=['is_active'])
    user.title = title_text
    user.flex_effect = 'title'
    user.save(update_fields=['title', 'flex_effect'])

    return Response({'success': True, 'title': title_text, 'coins_left': user.coins, 'message': f'Custom title "{title_text}" activated!'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_purchases(request):
    purchases = Purchase.objects.filter(user=request.user)[:3]
    data = [{
        'item': p.item.name,
        'icon': p.item.icon,
        'coins_spent': p.coins_spent,
        'purchased_at': p.purchased_at.isoformat(),
    } for p in purchases]
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redeem_promo(request):
    code = request.data.get('code', '').strip()
    if not code:
        return Response({'error': 'Enter a promo code.'}, status=status.HTTP_400_BAD_REQUEST)

    if code != '244466666':
        return Response({'error': 'Invalid or expired promo code.'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    coins_granted = 1_000_000
    diamonds_granted = 1_000_000
    user.coins += coins_granted
    user.diamonds += diamonds_granted
    user.save(update_fields=['coins', 'diamonds'])

    return Response({
        'success': True,
        'coins': user.coins,
        'diamonds': user.diamonds,
        'coins_granted': coins_granted,
        'diamonds_granted': diamonds_granted,
        'message': f'Redeemed! +{coins_granted:,} coins & +{diamonds_granted:,} diamonds',
    })
