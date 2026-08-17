from django.utils import timezone


def finalize_challenge(user, challenge, passed):
    if passed:
        challenge.status = 'completed'
        challenge.completed_at = timezone.now()
        xp_mult = 1 + (user.xp_boosts * 0.5)
        user.xp += int(challenge.xp_reward * xp_mult)
        user.coins += challenge.coin_reward
        new_level = user.xp // 1000 + 1
        if new_level > user.level:
            user.coins += 50
            user.level = new_level
        user.save(update_fields=['xp', 'coins', 'level'])
    else:
        challenge.status = 'submitted'
    challenge.save()
    return {
        'new_level': user.level,
        'total_xp': user.xp,
        'total_coins': user.coins,
    }
