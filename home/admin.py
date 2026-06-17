from django.contrib import admin
from .models import Challenge, ChatMessage, FriendRequest, CallSignal


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'user', 'category', 'difficulty', 'status',
        'xp_reward', 'coin_reward', 'quality_score', 'created_at',
    ]
    list_filter = [
        'status', 'difficulty', 'category', 'is_long', 'ai_checked',
        'created_at',
    ]
    search_fields = ['title', 'description', 'user__email', 'user__username', 'game_key']
    ordering = ['-created_at']
    list_per_page = 50
    readonly_fields = ['created_at', 'completed_at']
    autocomplete_fields = ['user']

    fieldsets = (
        ('Challenge', {
            'fields': ('user', 'category', 'title', 'description', 'game_key', 'link'),
        }),
        ('Rewards & Difficulty', {
            'fields': ('difficulty', 'xp_reward', 'coin_reward', 'is_long'),
        }),
        ('Proof', {
            'fields': ('proof_type', 'proof_text', 'proof_image',
                       'quality_score', 'feedback', 'ai_checked'),
        }),
        ('Status & Dates', {
            'fields': ('status', 'created_at', 'completed_at'),
        }),
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'role', 'created_at', 'truncated']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'user__email', 'user__username']
    ordering = ['-created_at']

    def truncated(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    truncated.short_description = 'Content'


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'from_user', 'to_user', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['from_user__email', 'from_user__username', 'to_user__email', 'to_user__username']


@admin.register(CallSignal)
class CallSignalAdmin(admin.ModelAdmin):
    list_display = ['id', 'caller', 'callee', 'signal_type', 'created_at']
    list_filter = ['signal_type', 'created_at']
    search_fields = ['caller__email', 'callee__email']
