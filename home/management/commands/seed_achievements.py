from django.core.management.base import BaseCommand
from home.models import Achievement, Title


ACHIEVEMENTS = [
    # Challenge Milestones
    {'name': 'First Step', 'desc': 'Complete your first challenge', 'cat': 'challenge', 'tier': 'bronze', 'icon': '👣', 'xp': 50, 'coins': 10, 'max': 1, 'secret': False, 'order': 1},
    {'name': 'Getting Warmed Up', 'desc': 'Complete 10 challenges', 'cat': 'challenge', 'tier': 'bronze', 'icon': '🔥', 'xp': 100, 'coins': 20, 'max': 10, 'secret': False, 'order': 2},
    {'name': 'Challenger', 'desc': 'Complete 50 challenges', 'cat': 'challenge', 'tier': 'silver', 'icon': '⚔️', 'xp': 300, 'coins': 75, 'max': 50, 'secret': False, 'order': 3},
    {'name': 'Veteran', 'desc': 'Complete 100 challenges', 'cat': 'challenge', 'tier': 'gold', 'icon': '🎖️', 'xp': 500, 'coins': 150, 'max': 100, 'secret': False, 'order': 4},
    {'name': 'Legend', 'desc': 'Complete 500 challenges', 'cat': 'challenge', 'tier': 'diamond', 'icon': '🏆', 'xp': 2000, 'coins': 500, 'max': 500, 'secret': False, 'order': 5},
    # Streaks
    {'name': 'On Fire', 'desc': '3 day streak', 'cat': 'streak', 'tier': 'bronze', 'icon': '🔥', 'xp': 75, 'coins': 15, 'max': 3, 'secret': False, 'order': 6},
    {'name': 'Week Warrior', 'desc': '7 day streak', 'cat': 'streak', 'tier': 'silver', 'icon': '📅', 'xp': 200, 'coins': 50, 'max': 7, 'secret': False, 'order': 7},
    {'name': 'Unstoppable', 'desc': '30 day streak', 'cat': 'streak', 'tier': 'gold', 'icon': '⚡', 'xp': 750, 'coins': 200, 'max': 30, 'secret': False, 'order': 8},
    {'name': 'Immortal', 'desc': '100 day streak', 'cat': 'streak', 'tier': 'diamond', 'icon': '♾️', 'xp': 3000, 'coins': 750, 'max': 100, 'secret': False, 'order': 9},
    # Multiplayer
    {'name': 'First Blood', 'desc': 'Win your first multiplayer match', 'cat': 'multiplayer', 'tier': 'bronze', 'icon': '🩸', 'xp': 100, 'coins': 25, 'max': 1, 'secret': False, 'order': 10},
    {'name': 'Competitor', 'desc': 'Win 10 multiplayer matches', 'cat': 'multiplayer', 'tier': 'silver', 'icon': '🤺', 'xp': 400, 'coins': 100, 'max': 10, 'secret': False, 'order': 11},
    {'name': 'Dominator', 'desc': 'Win 50 multiplayer matches', 'cat': 'multiplayer', 'tier': 'gold', 'icon': '👑', 'xp': 1000, 'coins': 250, 'max': 50, 'secret': False, 'order': 12},
    {'name': 'Undefeated', 'desc': 'Win 10 matches in a row', 'cat': 'multiplayer', 'tier': 'platinum', 'icon': '🏅', 'xp': 1500, 'coins': 400, 'max': 10, 'secret': False, 'order': 13},
    # Social
    {'name': 'Connected', 'desc': 'Add your first friend', 'cat': 'social', 'tier': 'bronze', 'icon': '🤝', 'xp': 50, 'coins': 10, 'max': 1, 'secret': False, 'order': 14},
    {'name': 'Social Butterfly', 'desc': 'Get 10 followers', 'cat': 'social', 'tier': 'silver', 'icon': '🦋', 'xp': 200, 'coins': 50, 'max': 10, 'secret': False, 'order': 15},
    # Shop
    {'name': 'First Purchase', 'desc': 'Buy something from the shop', 'cat': 'shop', 'tier': 'bronze', 'icon': '🛒', 'xp': 50, 'coins': 10, 'max': 1, 'secret': False, 'order': 16},
    {'name': 'Big Spender', 'desc': 'Spend 1000 coins total', 'cat': 'shop', 'tier': 'gold', 'icon': '💰', 'xp': 500, 'coins': 150, 'max': 1000, 'secret': False, 'order': 17},
    # Secret
    {'name': 'Night Owl', 'desc': 'Complete a challenge between 12am-4am', 'cat': 'secret', 'tier': 'silver', 'icon': '🦉', 'xp': 200, 'coins': 50, 'max': 1, 'secret': True, 'order': 18},
    {'name': 'Speed Demon', 'desc': 'Win a typing challenge with 100+ WPM', 'cat': 'secret', 'tier': 'gold', 'icon': '⚡', 'xp': 500, 'coins': 150, 'max': 1, 'secret': True, 'order': 19},
    {'name': 'Perfectionist', 'desc': 'Complete 10 challenges in a row with perfect score', 'cat': 'secret', 'tier': 'platinum', 'icon': '✨', 'xp': 1000, 'coins': 300, 'max': 10, 'secret': True, 'order': 20},
]

TITLES = [
    {'name': 'The Newcomer', 'tier': 'beginner', 'min_xp': 0, 'icon': '🌱', 'order': 1},
    {'name': 'Rising Challenger', 'tier': 'bronze', 'min_xp': 1000, 'icon': '🥉', 'order': 2},
    {'name': 'The Grinder', 'tier': 'silver', 'min_xp': 5000, 'icon': '🥈', 'order': 3},
    {'name': 'Elite Warrior', 'tier': 'gold', 'min_xp': 15000, 'icon': '🥇', 'order': 4},
    {'name': 'The Champion', 'tier': 'platinum', 'min_xp': 35000, 'icon': '💎', 'order': 5},
    {'name': 'The Untouchable', 'tier': 'diamond', 'min_xp': 75000, 'icon': '👑', 'order': 6},
]


class Command(BaseCommand):
    help = 'Seed achievements and titles into the database'

    def handle(self, *args, **options):
        for a in ACHIEVEMENTS:
            Achievement.objects.update_or_create(
                name=a['name'],
                defaults={
                    'description': a['desc'],
                    'category': a['cat'],
                    'tier': a['tier'],
                    'icon': a['icon'],
                    'xp_reward': a['xp'],
                    'coin_reward': a['coins'],
                    'max_progress': a['max'],
                    'secret': a['secret'],
                    'order': a['order'],
                }
            )
        self.stdout.write(f'Seeded {len(ACHIEVEMENTS)} achievements')

        for t in TITLES:
            Title.objects.update_or_create(
                name=t['name'],
                defaults={
                    'tier': t['tier'],
                    'min_xp': t['min_xp'],
                    'icon': t['icon'],
                    'order': t['order'],
                }
            )
        self.stdout.write(f'Seeded {len(TITLES)} titles')
