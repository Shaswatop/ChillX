from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from home.models import ShopItem, Raffle


class Command(BaseCommand):
    help = 'Seed the shop with items and a raffle'

    def handle(self, *args, **options):
        items = [
            # Hot Deals — MONEY only
            {'name': 'XP Surge', 'description': '2x XP for 24 hours', 'category': 'hot', 'rarity': 'epic',
             'price_coins': 800, 'discount_percent': 38, 'icon': '⚡', 'is_featured': True, 'sort_order': 1, 'price_gems': 0},
            {'name': 'Streak Shield', 'description': 'Protect your streak for 1 missed day', 'category': 'hot', 'rarity': 'rare',
             'price_coins': 300, 'icon': '🛡️', 'sort_order': 2, 'price_gems': 0},
            {'name': 'Challenge Skip', 'description': 'Skip any challenge you don\'t want', 'category': 'hot', 'rarity': 'common',
             'price_coins': 150, 'icon': '🎯', 'sort_order': 3, 'price_gems': 0},
            {'name': 'Hint Token x3', 'description': 'Reveal hints on hard challenges', 'category': 'hot', 'rarity': 'common',
             'price_coins': 200, 'icon': '💡', 'sort_order': 4, 'price_gems': 0},
            # Boosts — MONEY only
            {'name': 'XP Boost 2x / 24hr', 'description': 'Double XP for 24 hours', 'category': 'boosts', 'rarity': 'rare',
             'price_coins': 500, 'icon': '⚡', 'sort_order': 5, 'price_gems': 0},
            {'name': 'XP Boost 2x / 72hr', 'description': 'Double XP for 3 days (BEST VALUE)', 'category': 'boosts', 'rarity': 'epic',
             'price_coins': 1200, 'icon': '⚡', 'sort_order': 6, 'price_gems': 0},
            {'name': 'Coin Multiplier 1.5x', 'description': '1.5x coins for 24 hours', 'category': 'boosts', 'rarity': 'rare',
             'price_coins': 400, 'icon': '🔥', 'sort_order': 7, 'price_gems': 0},
            {'name': 'Weekend Warrior Pass', 'description': '2x coins all weekend', 'category': 'boosts', 'rarity': 'epic',
             'price_coins': 600, 'icon': '📅', 'sort_order': 8, 'price_gems': 0},
            {'name': 'Challenge Reroll x3', 'description': 'Reroll 3 challenges', 'category': 'boosts', 'rarity': 'common',
             'price_coins': 250, 'icon': '🔄', 'sort_order': 9, 'price_gems': 0},
            {'name': 'Mega Shield (3 days)', 'description': '3-day streak protection', 'category': 'boosts', 'rarity': 'rare',
             'price_coins': 750, 'icon': '🛡️', 'sort_order': 10, 'price_gems': 0},
            # Flex & Titles — DIAMONDS only
            {'name': 'Title: Nepal #1', 'description': 'Exclusive Nepal #1 title', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '👑', 'is_limited': True, 'stock_remaining': 100, 'is_featured': True, 'sort_order': 11, 'price_gems': 50},
            {'name': 'Title: Grinder', 'description': 'Show off your grind', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '👑', 'sort_order': 12, 'price_gems': 20},
            {'name': 'Title: Early OG', 'description': 'OG status forever', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '👑', 'is_limited': True, 'stock_remaining': 100, 'sort_order': 13, 'price_gems': 80},
            {'name': 'Animated Rainbow Name', 'description': 'Rainbow animated username', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🌈', 'sort_order': 14, 'price_gems': 30},
            {'name': 'Gold Username', 'description': 'Gold username color', 'category': 'flex', 'rarity': 'rare',
             'price_coins': 0, 'icon': '✨', 'sort_order': 15, 'price_gems': 15},
            {'name': 'Flame Profile Border', 'description': 'Animated flame border', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🔥', 'sort_order': 16, 'price_gems': 25},
            {'name': 'Electric Profile Border', 'description': 'Animated electric border', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '⚡', 'sort_order': 17, 'price_gems': 25},
            {'name': 'Shooting Star Effect', 'description': 'Shooting star profile effect', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌟', 'sort_order': 18, 'price_gems': 40},
            {'name': 'Blood Moon Effect', 'description': 'Deep red pulsing border with dripping blood name', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌑', 'sort_order': 19, 'price_gems': 55},
            {'name': 'Void Effect', 'description': 'Dark matter warping border', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🕳️', 'sort_order': 20, 'price_gems': 60},
            {'name': 'Holographic Name', 'description': 'Prismatic shimmer holographic name', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '💿', 'sort_order': 21, 'price_gems': 50},
            {'name': 'Matrix Rain', 'description': 'Cascading green digits rain effect', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '👾', 'sort_order': 22, 'price_gems': 55},
            {'name': 'Angel Effect', 'description': 'Holy white glow with floating animation', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '😇', 'sort_order': 23, 'price_gems': 60},
            {'name': 'Demon Effect', 'description': 'Hellfire border with flickering name', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '😈', 'sort_order': 24, 'price_gems': 65},
            {'name': 'Galaxy Effect', 'description': 'Orbiting stars with nebula background', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌌', 'sort_order': 25, 'price_gems': 70},
            {'name': 'Neon Sign', 'description': 'Flickering neon tube border and name', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '💡', 'sort_order': 26, 'price_gems': 45},
            {'name': 'Cyberpunk Effect', 'description': 'Scanlines with digital glitch name', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🦾', 'sort_order': 27, 'price_gems': 45},
            {'name': 'Sakura Effect', 'description': 'Falling cherry blossom petals', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🌸', 'sort_order': 28, 'price_gems': 40},
            {'name': 'Lava Effect', 'description': 'Molten gold-orange drip border', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🌋', 'sort_order': 29, 'price_gems': 45},
            {'name': 'Shadow Effect', 'description': 'Dark presence creeping darkness', 'category': 'flex', 'rarity': 'rare',
             'price_coins': 0, 'icon': '🌑', 'sort_order': 30, 'price_gems': 25},
            {'name': 'Thunder Effect', 'description': 'Lightning strike flash effect', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '⛈️', 'sort_order': 31, 'price_gems': 40},
            {'name': 'Saturn Ring', 'description': 'Spinning orbital ring around avatar', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🪐', 'sort_order': 32, 'price_gems': 45},
            {'name': 'Cursed Effect', 'description': 'Inverted flicker with glitchy spacing', 'category': 'flex', 'rarity': 'rare',
             'price_coins': 0, 'icon': '🫠', 'sort_order': 33, 'price_gems': 20},
            {'name': 'Crypto Ticker', 'description': 'Scrolling crypto ticker bar', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '📈', 'sort_order': 34, 'price_gems': 35},
            {'name': 'Pixel Name', 'description': '8-bit retro pixel style', 'category': 'flex', 'rarity': 'rare',
             'price_coins': 0, 'icon': '🕹️', 'sort_order': 35, 'price_gems': 20},
            {'name': 'Dragon Effect', 'description': 'Scales pattern with dragon fire breath', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🐉', 'sort_order': 36, 'price_gems': 75},
            {'name': 'Sunrise Effect', 'description': 'Warm gradient sunrise wave', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌅', 'sort_order': 37, 'price_gems': 55},
            {'name': 'Overloaded Effect', 'description': 'Rapid hue rotation max chaos', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '💥', 'sort_order': 38, 'price_gems': 100},
            {'name': 'Bounty Hunter', 'description': 'Wanted poster dashed border', 'category': 'flex', 'rarity': 'rare',
             'price_coins': 0, 'icon': '🤠', 'sort_order': 39, 'price_gems': 25},
            {'name': 'Frostbite Effect', 'description': 'Crystallize expanding ice border', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🧊', 'sort_order': 40, 'price_gems': 40},
            {'name': 'Nepal Name', 'description': 'Red-white Nepal flag shimmer', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🇳🇵', 'sort_order': 41, 'price_gems': 50},
            {'name': 'Toxic Name', 'description': 'Green toxic neon glow name', 'category': 'flex', 'rarity': 'rare',
             'price_coins': 0, 'icon': '☠️', 'sort_order': 42, 'price_gems': 20},
            {'name': 'Ice Border', 'description': 'Frozen ice crystal border', 'category': 'flex', 'rarity': 'rare',
             'price_coins': 0, 'icon': '❄️', 'sort_order': 43, 'price_gems': 20},
            # Avatar FX (bg_effect) — DIAMONDS only
            {'name': 'Sakura Storm', 'description': 'Rose-pink sakura petals falling across your profile', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌸', 'sort_order': 45, 'price_gems': 60},
            {'name': 'Ocean Depths', 'description': 'Deep ocean teal animated waves background', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌊', 'sort_order': 46, 'price_gems': 55},
            {'name': 'Sunset Horizon', 'description': 'Warm orange-purple sunset gradient background', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌅', 'sort_order': 47, 'price_gems': 55},
            {'name': 'Cosmic Nebula', 'description': 'Space nebula purple-blue with drifting particles', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌌', 'sort_order': 48, 'price_gems': 70},
            {'name': 'Neon Grid', 'description': 'Cyberpunk neon grid with scanning lines', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🏙️', 'sort_order': 49, 'price_gems': 45},
            {'name': 'Starry Sky', 'description': 'Animated twinkling starry night sky', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '✨', 'sort_order': 50, 'price_gems': 40},
            {'name': 'Lava Flow', 'description': 'Molten lava cracking orange-red background', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌋', 'sort_order': 51, 'price_gems': 60},
            {'name': 'Crystal Aura', 'description': 'Blue crystal geometric shimmer aura', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '💎', 'sort_order': 52, 'price_gems': 45},
            {'name': 'Frostwind', 'description': 'Icy wind particles with frost effect', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '❄️', 'sort_order': 53, 'price_gems': 40},
            {'name': 'Thunder Storm', 'description': 'Dark storm with lightning flash effects', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '⛈️', 'sort_order': 54, 'price_gems': 65},
            {'name': 'Fire Spirit', 'description': 'Rising flame particles with ember glow', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🔥', 'sort_order': 55, 'price_gems': 60},
            {'name': 'Mystic Mist', 'description': 'Purple mystic mist aura swirling effect', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌫️', 'sort_order': 56, 'price_gems': 55},
            {'name': 'Stardust Burst', 'description': 'Rainbow stardust particles bursting across your profile', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '✨', 'sort_order': 57, 'price_gems': 70},
            {'name': 'Ember Sparks', 'description': 'Flying ember sparks with warm glow', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🔥', 'sort_order': 58, 'price_gems': 45},
            {'name': 'Snowfall', 'description': 'Heavy snow falling with frozen mist', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '❄️', 'sort_order': 59, 'price_gems': 40},
            {'name': 'Energy Arc', 'description': 'Blue electric energy arcs crackling', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '⚡', 'sort_order': 60, 'price_gems': 65},
            {'name': 'Neon Rain', 'description': 'Colorful neon rain falling in cyberpunk style', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🌧️', 'sort_order': 61, 'price_gems': 60},
            {'name': 'Spirit Orbs', 'description': 'Floating mystical spirit orbs with trail', 'category': 'flex', 'rarity': 'legendary',
             'price_coins': 0, 'icon': '🔮', 'sort_order': 62, 'price_gems': 55},
            {'name': 'Glitch Name', 'description': 'Digital glitch corrupt name', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🔄', 'sort_order': 44, 'price_gems': 30},
            {'name': 'Global Shoutout 24hr', 'description': 'Shoutout on global feed', 'category': 'flex', 'rarity': 'rare',
             'price_coins': 0, 'icon': '📢', 'sort_order': 19, 'price_gems': 10},
            {'name': 'Leaderboard Pin 24hr', 'description': 'Pinned on leaderboard for 24hr', 'category': 'flex', 'rarity': 'epic',
             'price_coins': 0, 'icon': '🏅', 'sort_order': 20, 'price_gems': 20},
            # Loot Boxes — Basic/Mystery = MONEY, Epic/Legendary = DIAMONDS
            {'name': 'Basic Crate', 'description': 'Contains 1 random Common or Rare item', 'category': 'lootbox', 'rarity': 'common',
             'price_coins': 300, 'icon': '📦', 'sort_order': 21, 'price_gems': 0},
            {'name': 'Epic Crate', 'description': '1 guaranteed Rare, chance at Epic', 'category': 'lootbox', 'rarity': 'epic',
             'price_coins': 0, 'icon': '📦', 'sort_order': 22, 'price_gems': 12},
            {'name': 'Legendary Crate', 'description': '1 guaranteed Epic, chance at Legendary', 'category': 'lootbox',
             'rarity': 'legendary', 'price_coins': 0, 'icon': '📦', 'is_featured': True, 'sort_order': 23, 'price_gems': 30},
            {'name': 'Mystery Box', 'description': 'Could be anything... even Legendary (2% chance)', 'category': 'lootbox',
             'rarity': 'legendary', 'price_coins': 500, 'icon': '🎁', 'sort_order': 24, 'price_gems': 0},
            # Cosmetics / AI — MONEY only
            {'name': 'AI Profile Pic Generator', 'description': 'Upload a selfie and get a cool AI-styled profile pic (anime, neon, vintage, glitch styles). Auto-sets as your avatar + downloadable!', 'category': 'cosmetics',
             'rarity': 'epic', 'price_coins': 1500, 'icon': '🤖', 'sort_order': 25, 'price_gems': 0},
        ]

        created = 0
        updated = 0
        for data in items:
            obj, was_created = ShopItem.objects.update_or_create(name=data['name'], defaults=data)
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} shop items, updated {updated} with price_gems'))

        if not Raffle.objects.filter(is_active=True).exists() or True:
            raffle, created = Raffle.objects.get_or_create(
                prize_name='NPR 500 eSewa / Gift Card',
                defaults={
                    'prize_value': 'NPR 500',
                    'ticket_price': 100,
                    'max_tickets_per_user': 10,
                    'max_total_tickets': 500,
                    'ends_at': timezone.now() + timedelta(days=3),
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS('Created active raffle'))
            else:
                raffle.ends_at = timezone.now() + timedelta(days=3)
                raffle.save(update_fields=['ends_at'])
                self.stdout.write(self.style.SUCCESS('Updated raffle end time'))
