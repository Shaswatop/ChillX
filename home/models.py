from django.db import models
from django.conf import settings


class Challenge(models.Model):
    DIFFICULTIES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('nightmare', 'Nightmare'),
    ]
    STATUSES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]
    PROOF_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('both', 'Both'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='challenges')
    category = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.TextField()
    xp_reward = models.IntegerField(default=50)
    coin_reward = models.IntegerField(default=10)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTIES, default='medium')
    proof_type = models.CharField(max_length=10, choices=PROOF_TYPES, default='text')
    is_long = models.BooleanField(default=False)
    link = models.URLField(max_length=500, blank=True, default='')
    game_key = models.CharField(max_length=30, blank=True, default='', help_text='In-app game this challenge links to (typing, reaction, cps, aim3d, memory, tictactoe, runner)')
    created_at = models.DateField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    proof_text = models.TextField(blank=True)
    proof_image = models.TextField(blank=True)
    quality_score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    ai_checked = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at', 'category']

    def __str__(self):
        return f"[{self.category}] {self.title} ({self.difficulty})"


class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    role = models.CharField(max_length=10)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class UserGameStats(models.Model):
    """Per-user stats for each in-house mini-game (high scores, wins/losses, death counts, etc.)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='game_stats',
    )
    game = models.CharField(max_length=30)
    best_score = models.IntegerField(default=0)
    best_score_secondary = models.IntegerField(default=0, help_text='Second metric (e.g. accuracy for typing)')
    plays = models.IntegerField(default=0)
    wins = models.IntegerField(default=0, help_text='Multiplayer arena wins for this game')
    losses = models.IntegerField(default=0, help_text='Multiplayer arena losses for this game')
    deaths = models.IntegerField(default=0, help_text='Total deaths across all sessions (e.g. runner game)')
    last_played = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'game')]
        ordering = ['game']

    @property
    def win_rate(self):
        total = self.wins + self.losses
        return round(self.wins / total * 100, 1) if total > 0 else 0.0

    def __str__(self):
        return f"{self.user_id} / {self.game}: {self.best_score}"


# ── SHOP MODELS ──

class ShopItem(models.Model):
    CATEGORIES = [
        ('boosts', 'Boosts'),
        ('flex', 'Flex & Titles'),
        ('lootbox', 'Loot Boxes'),
        ('raffle', 'Raffle'),
        ('cosmetics', 'Cosmetics'),
        ('bundles', 'Bundles'),
        ('hot', 'Hot Deals'),
    ]
    RARITIES = [
        ('common', 'Common'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    rarity = models.CharField(max_length=20, choices=RARITIES, default='common')
    price_coins = models.IntegerField(default=0)
    price_gems = models.IntegerField(default=0)
    icon = models.CharField(max_length=50, blank=True, default='')
    is_limited = models.BooleanField(default=False)
    stock_remaining = models.IntegerField(default=-1)
    is_featured = models.BooleanField(default=False)
    discount_percent = models.IntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', '-created_at']

    @property
    def sale_price(self):
        if self.discount_percent > 0:
            return int(self.price_coins * (100 - self.discount_percent) / 100)
        return self.price_coins

    def __str__(self):
        return f"[{self.get_rarity_display()}] {self.name}"


class UserInventory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-purchased_at']
        unique_together = [('user', 'item')]

    def __str__(self):
        return f"{self.user} owns {self.item.name}"


class Purchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchases')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    coins_spent = models.IntegerField()
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-purchased_at']

    def __str__(self):
        return f"{self.user} bought {self.item.name} for {self.coins_spent}"


class Raffle(models.Model):
    prize_name = models.CharField(max_length=200)
    prize_value = models.CharField(max_length=100, blank=True)
    ticket_price = models.IntegerField(default=100)
    max_tickets_per_user = models.IntegerField(default=10)
    max_total_tickets = models.IntegerField(default=500)
    ends_at = models.DateTimeField()
    winner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Raffle: {self.prize_name}"


class RaffleTicket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='raffle_tickets')
    raffle = models.ForeignKey(Raffle, on_delete=models.CASCADE, related_name='tickets')
    quantity = models.IntegerField(default=1)
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} x{self.quantity} tickets for {self.raffle.prize_name}"


# ── SOCIAL / CHILLX MODELS ──

class SocialPost(models.Model):
    challenge = models.ForeignKey(Challenge, null=True, blank=True, on_delete=models.SET_NULL, related_name='social_posts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_posts')
    category = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    proof_text = models.TextField(blank=True)
    proof_image = models.TextField(blank=True)
    proof_video = models.TextField(blank=True)
    vote_score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.category}] {self.title}"


class Comment(models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user} on {self.post.id}"


class Vote(models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    value = models.IntegerField(default=0)

    class Meta:
        unique_together = [('post', 'user')]

    def __str__(self):
        return f"{self.user} voted {self.value} on {self.post.id}"


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following_set')
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers_set')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('follower', 'following')]

    def __str__(self):
        return f"{self.follower} follows {self.following}"


class FriendRequest(models.Model):
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_friend_requests')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=10, choices=[('pending','Pending'),('accepted','Accepted'),('rejected','Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('from_user', 'to_user')]

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"


class Story(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stories')
    image = models.TextField(blank=True)
    video = models.TextField(blank=True)
    text = models.TextField(blank=True)
    text_style = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Story by {self.user} at {self.created_at}"


# ── CHATX MODEL ──

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(blank=True)
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    image = models.TextField(blank=True)
    video = models.TextField(blank=True)
    file = models.TextField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Msg {self.id} from {self.sender} to {self.receiver}"


class CallSignal(models.Model):
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='call_signals_sent')
    callee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='call_signals_received')
    signal_type = models.CharField(max_length=20, choices=[
        ('offer', 'Offer'),
        ('answer', 'Answer'),
        ('ice', 'ICE Candidate'),
        ('end', 'End Call'),
    ])
    data = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"CallSignal {self.signal_type} from {self.caller} to {self.callee}"


class Achievement(models.Model):
    CATEGORY_CHOICES = [
        ('challenge', 'Challenge Milestones'),
        ('streak', 'Streaks'),
        ('multiplayer', 'Multiplayer'),
        ('social', 'Social'),
        ('shop', 'Shop'),
        ('secret', 'Secret'),
    ]
    TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond'),
    ]
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    tier = models.CharField(max_length=10, choices=TIER_CHOICES)
    icon = models.CharField(max_length=10, default='🏆')
    xp_reward = models.IntegerField(default=50)
    coin_reward = models.IntegerField(default=10)
    max_progress = models.IntegerField(default=1)
    secret = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='user_achievements')
    progress = models.IntegerField(default=0)
    unlocked = models.BooleanField(default=False)
    unlocked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'achievement')

    def __str__(self):
        return f"{self.user} - {self.achievement} ({self.progress}/{self.achievement.max_progress})"


class Title(models.Model):
    TIER_CHOICES = [
        ('beginner', 'Beginner'),
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond'),
    ]
    name = models.CharField(max_length=100)
    tier = models.CharField(max_length=10, choices=TIER_CHOICES)
    min_xp = models.IntegerField(default=0)
    icon = models.CharField(max_length=10, default='👑')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class UserTitle(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_titles')
    title = models.ForeignKey(Title, on_delete=models.CASCADE, related_name='user_titles')
    unlocked = models.BooleanField(default=False)
    equipped = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'title')

    def __str__(self):
        return f"{self.user} - {self.title} {'(equipped)' if self.equipped else ''}"
