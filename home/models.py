from django.db import models
from django.conf import settings


# A daily challenge a user gets (typing, quiz, fitness, etc).
# If removed, the challenges page and all verify_* views break.
# Change fields here + run makemigrations to add/remove columns.
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
    objective = models.CharField(max_length=200, blank=True, default='', help_text='Structured objective, e.g. "reach the target"')
    metric = models.CharField(max_length=50, blank=True, default='', help_text='Measured metric, e.g. wpm, accuracy, cps, ms, score')
    target = models.FloatField(null=True, blank=True, help_text='Numeric target for the metric')
    unit = models.CharField(max_length=20, blank=True, default='', help_text='Unit for the target, e.g. wpm, %, seconds, reps')
    estimated_duration = models.CharField(max_length=50, blank=True, default='', help_text='Rough effort, e.g. "3 minutes"')
    special_condition = models.TextField(blank=True, default='', help_text='Optional mechanic/special condition')
    ai_meta = models.JSONField(blank=True, default=dict, help_text='Raw validated AI payload for auditing')
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


# Stores a single chat line with the AI companion (challenge chat page).
# If removed, the challenge chat history won't save.
# Created from challenge_chat view in home/views.py.
class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    role = models.CharField(max_length=10)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# Per-user stats for each mini-game (best score, plays, wins, losses, deaths).
# If removed, the dashboard game stats and save_game_stats API break.
# Written from the verify_* views and multiplayer results.
class UserGameStats(models.Model):
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


# Shop item a user can buy (boost, cosmetic, loot box, raffle ticket, etc).
# If removed, the shop page and inventory break.
# Seeded by the seed_shop command; buy logic in shop_views.py.
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


# Which shop items a user owns + whether it's active/equipped.
# If removed, inventory page and equip/unequip break.
# Created when a purchase succeeds in shop_views.py.
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


# Records every shop purchase (who bought what for how much).
# If removed, the "recent purchases" widget breaks.
# Created in shop_views.py shop_buy.
class Purchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchases')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    coins_spent = models.IntegerField()
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-purchased_at']

    def __str__(self):
        return f"{self.user} bought {self.item.name} for {self.coins_spent}"


# A raffle event users can buy tickets for.
# If removed, the raffle section of the shop breaks.
# Managed from shop_views.py raffle endpoints.
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


# Tracks how many raffle tickets each user bought for a raffle.
# If removed, buying/entering raffles stops working.
# Created in shop_views.py raffle_buy.
class RaffleTicket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='raffle_tickets')
    raffle = models.ForeignKey(Raffle, on_delete=models.CASCADE, related_name='tickets')
    quantity = models.IntegerField(default=1)
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} x{self.quantity} tickets for {self.raffle.prize_name}"


# SOCIAL / CHILLX MODELS

# A post a user shares on the ChillX social feed.
# If removed, the social feed and share-results feature break.
# Created via social_create_post in home/views.py.
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


# A reply on a social post.
# If removed, social_post comments break.
# Created via social_comment view.
class Comment(models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user} on {self.post.id}"


# One upvote/downvote on a social post.
# If removed, voting on posts stops working.
# Created via social_vote view.
class Vote(models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    value = models.IntegerField(default=0)

    class Meta:
        unique_together = [('post', 'user')]

    def __str__(self):
        return f"{self.user} voted {self.value} on {self.post.id}"


# Who follows who on the social feed.
# If removed, the follow button stops working.
# Created via toggle_follow view.
class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following_set')
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers_set')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('follower', 'following')]

    def __str__(self):
        return f"{self.follower} follows {self.following}"


# A friend request between two users (must be accepted).
# If removed, the friend system breaks.
# Created via send_friend_request / respond_friend_request views.
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


# A 24-hour story on the social feed (image/video/text).
# If removed, the stories row breaks.
# Created via create_story view.
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


# CHATX MODEL

# A private chat message in ChatX (sender, receiver, text/image/video/file).
# If removed, ChatX breaks entirely.
# Created via send_message view; polled by get_messages.
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


# One WebRTC signal (offer/answer/ICE/end) passed between callers.
# If removed, voice/video calls break.
# Created via send_call_signal / poll_call_signals views.
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


# A badge/achievement definition (name, tier, rewards, max progress).
# If removed, the achievements page and rewards break.
# Seeded by the seed_achievements command.
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


# A user's progress toward one achievement.
# If removed, achievement progress tracking breaks.
# Updated in achievement_views.py update_achievement_progress.
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


# A display title users can unlock/equip based on XP.
# If removed, the titles feature breaks.
# Seeded by seed_achievements; equipped via equip_title view.
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


# Links a user to a title they've unlocked/equipped.
# If removed, equipping titles breaks.
# Managed in achievement_views.py.
class UserTitle(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_titles')
    title = models.ForeignKey(Title, on_delete=models.CASCADE, related_name='user_titles')
    unlocked = models.BooleanField(default=False)
    equipped = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'title')

    def __str__(self):
        return f"{self.user} - {self.title} {'(equipped)' if self.equipped else ''}"
