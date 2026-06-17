from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = [
        'email', 'username', 'display_name', 'level', 'xp',
        'coins', 'rerolls', 'is_staff', 'is_active', 'date_joined',
    ]
    list_filter = [
        'is_staff', 'is_active', 'is_superuser', 'theme',
        'daily_challenges_generated', 'date_joined',
    ]
    search_fields = ['email', 'username', 'display_name']
    ordering = ['-date_joined']
    list_per_page = 50
    readonly_fields = ['last_login', 'date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Identity', {'fields': ('username', 'display_name', 'title', 'bio', 'avatar', 'avatar_base64', 'avatar_frame', 'theme')}),
        ('Economy & Progress', {
            'fields': (
                'coins', 'xp', 'level', 'daily_challenges_generated',
                'xp_boosts', 'rerolls', 'streak_freezes', 'last_free_reroll_date',
                
            )
        }),
        ('Preferences & AI', {
            'fields': (
                'preferences', 'difficulty_pref', 'daily_challenge_count',
                'ai_name', 'ai_avatar_base64', 'ai_personality',
            )
        }),
        ('Notifications', {
            'fields': (
                'notify_xp', 'notify_badges', 'notify_friend_activity',
                'notify_leaderboard', 'notify_streak',
            )
        }),
        ('Privacy', {'fields': ('profile_visibility', 'who_can_follow')}),
        ('API Keys', {
            'classes': ('collapse',),
            'fields': ('groq_api_key', 'gemini_api_key', 'openrouter_api_key',
                       'groq_model', 'gemini_model', 'openrouter_model'),
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Data', {'fields': ('challenge_history', 'contracts')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )
