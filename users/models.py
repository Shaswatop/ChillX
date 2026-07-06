from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    display_name = models.CharField(max_length=30, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    avatar_base64 = models.TextField(blank=True)
    preferences = models.JSONField(default=list, blank=True)

    # Profile & Personalization
    title = models.CharField(max_length=50, blank=True, default='')
    theme = models.CharField(max_length=30, default='dark-purple')
    avatar_frame = models.CharField(max_length=30, blank=True, default='none')

    # Challenge Preferences
    difficulty_pref = models.CharField(max_length=20, default='medium')
    daily_challenge_count = models.IntegerField(default=3)

    # Notifications
    notify_xp = models.BooleanField(default=True)
    notify_badges = models.BooleanField(default=True)
    notify_friend_activity = models.BooleanField(default=True)
    notify_leaderboard = models.BooleanField(default=True)
    notify_streak = models.BooleanField(default=True)

    # Privacy & Social
    profile_visibility = models.CharField(max_length=20, default='public')
    who_can_follow = models.CharField(max_length=20, default='everyone')

    # Economy
    coins = models.IntegerField(default=500)
    diamonds = models.IntegerField(default=0)
    flex_effect = models.CharField(max_length=50, blank=True, default='')
    name_effect = models.CharField(max_length=50, blank=True, default='')
    avatar_border = models.CharField(max_length=50, blank=True, default='')
    bg_effect = models.CharField(max_length=50, blank=True, default='')
    custom_title = models.CharField(max_length=50, blank=True, default='')
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    daily_challenges_generated = models.DateField(null=True, blank=True)

    # Inventory / Boosts
    xp_boosts = models.IntegerField(default=0)
    rerolls = models.IntegerField(default=0)
    streak_freezes = models.IntegerField(default=0)
    profile_pic_generations = models.IntegerField(default=0)
    last_free_reroll_date = models.DateField(null=True, blank=True)

    # Challenge history (titles to avoid AI repeats)
    challenge_history = models.JSONField(default=list, blank=True)

    # Accountability contracts stored as JSON
    contracts = models.JSONField(default=list, blank=True)

    # AI Companion
    ai_name = models.CharField(max_length=50, blank=True, default='ChillX')
    ai_avatar_base64 = models.TextField(blank=True, default='')
    ai_personality = models.TextField(blank=True, default='', help_text='Memory & personalization details for your AI companion')

    # Custom API Keys
    groq_api_key = models.CharField(max_length=200, blank=True, default='')
    gemini_api_key = models.CharField(max_length=200, blank=True, default='')
    openrouter_api_key = models.CharField(max_length=200, blank=True, default='')

    # Model Selections
    groq_model = models.CharField(max_length=100, blank=True, default='llama-3.3-70b-versatile')
    gemini_model = models.CharField(max_length=100, blank=True, default='gemini-1.5-flash')
    openrouter_model = models.CharField(max_length=100, blank=True, default='openai/gpt-4o-mini')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
