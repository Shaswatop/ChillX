from datetime import date
import random
from .models import Challenge
from .ai_service import generate_challenges_stream, generate_challenges as ai_generate


# Map user-pref categories to a deterministic filler strategy
_PREF_TO_FILLER = {
    'coding':   'offline_coding',
    'art':      'offline_art',
    'fitness':  'offline_fitness',
    'quiz':     'offline_quiz',
    'typing':   'inapp:typing',
    'reaction': 'inapp:reaction',
    'cps':      'inapp:cps',
    'gaming':   'poki_random',
}


def balance_categories(ai_results, user_prefs, level, needed=None):
    """Safety net: ensure every user pref is represented at least once.

    The AI is asked to distribute categories evenly, but LLMs can drop one.
    For each missing pref, pull a deterministic challenge from the offline
    example pool (art/fitness/coding) or build an in-app
    challenge (typing/reaction/cps) or pick a poki game (gaming).
    """
    from .challenge_catalog import (
        get_inapp_challenge, get_poki_challenge, POKI_GAMES,
    )
    present = {c.get('category') for c in ai_results}
    missing = [p for p in user_prefs if p not in present]
    if not missing:
        return ai_results

    out = list(ai_results)
    for pref in missing:
        strategy = _PREF_TO_FILLER.get(pref)
        if not strategy:
            continue
        if strategy.startswith('offline_'):
            cat = strategy.split('_', 1)[1]
            from .challenge_catalog import OFFLINE_FEW_SHOT_EXAMPLES
            pool = [e for e in OFFLINE_FEW_SHOT_EXAMPLES if e.get('category') == cat]
            if not pool:
                pool = [e for e in OFFLINE_FEW_SHOT_EXAMPLES]
            if pool:
                # Pick a random one, then scale to user level via _band
                ex = random.choice(pool)
                cd = dict(ex)  # copy
                cd['_band'] = 'medium'
                out.append(cd)
        elif strategy.startswith('inapp:'):
            gk = strategy.split(':', 1)[1]
            ch = get_inapp_challenge(gk, level)
            if ch:
                out.append(ch)
        elif strategy == 'poki_random':
            pg = random.choice(POKI_GAMES)
            ch = get_poki_challenge(pg['key'], level)
            if ch:
                out.append(ch)
    return out


def get_todays_challenges(user):
    """Get today's existing pending challenges. Does NOT auto-generate."""
    today = date.today()
    return list(Challenge.objects.filter(
        user=user,
        created_at=today,
        status='pending'
    ))


def auto_generate_daily(user):
    """
    Auto-generate today's challenge batch on first visit of the day.

    Trained-aware: this is the "training run" for the AI. Each visit, we feed
    the user profile + few-shot catalog into the prompt so generated
    challenges are tailored to this user's level, strengths, and trend.

    Idempotent: if today's challenges are already generated, do nothing.
    """
    today = date.today()
    if user.daily_challenges_generated == today:
        return []  # already done

    count = user.daily_challenge_count or 3
    categories = user.preferences or [
        'coding', 'gaming', 'typing', 'reaction', 'cps',
        'art', 'fitness', 'quiz',
    ]
    difficulty = user.difficulty_pref or 'medium'
    history = user.challenge_history or []

    # Try AI generation with full trained context
    created = []
    streamed = []
    try:
        for cd in generate_challenges_stream(
            categories, difficulty, count + 3, history,
            level=user.level, user=user,
        ):
            streamed.append(cd)
            if len(streamed) >= count + 3:
                break
    except Exception:
        pass

    # Safety net: balance categories to cover every user pref
    balanced = []
    if streamed:
        try:
            balanced = balance_categories(streamed, categories, user.level)
        except Exception:
            balanced = list(streamed)

    # Prioritise fillers (cover missing prefs) over AI gaming duplicates
    ai_titles = {c.get('title') for c in streamed}
    fillers = [c for c in balanced if c.get('title') not in ai_titles]
    ai_picks = [c for c in balanced if c.get('title') in ai_titles]

    # Dedup: drop AI picks whose title duplicates within the batch
    seen_titles = set()
    deduped = []
    for c in ai_picks:
        t = c.get('title', '')
        if t and t not in seen_titles:
            deduped.append(c)
            seen_titles.add(t)

    # Deduplicate AI picks by category, drop unexpected ones first
    seen_cats = set()
    kept = []
    extras = []
    for c in deduped:
        if c.get('category') in seen_cats or c.get('category') not in categories:
            extras.append(c)
        else:
            kept.append(c)
            seen_cats.add(c.get('category'))

    # Assemble final list: fillers first (guaranteed coverage), then unique AI picks
    to_save = fillers + kept
    # If we still have room, pull back from extras
    if len(to_save) < count:
        to_save.extend(extras[:count - len(to_save)])

    for i, cd in enumerate(to_save[:count]):
        is_long = (i == count - 1)
        ch = generate_and_save_challenge(user, cd, difficulty, is_long)
        created.append(ch)

    # Catalog fallback: use verified challenges with working links
    if not created:
        from .challenge_catalog import (
            get_inapp_challenge, get_poki_challenge, get_offline_challenge,
            IN_APP_GAMES, POKI_GAMES,
        )
        inapp_keys = list(IN_APP_GAMES.keys())
        poki_keys = [g['key'] for g in POKI_GAMES]
        for i in range(count):
            is_long = (i == count - 1)
            picker = random.choice([
                lambda: get_inapp_challenge(random.choice(inapp_keys), user.level),
                lambda: get_poki_challenge(random.choice(poki_keys), user.level),
                lambda: get_offline_challenge(
                    random.choice(categories) if categories else "general",
                    user.level,
                ),
            ])
            cd = picker()
            if cd:
                ch = generate_and_save_challenge(user, cd, difficulty, is_long)
                created.append(ch)

    # Last-resort fallback: hardcoded defaults
    if not created:
        for i, cd in enumerate(_fallback_challenges(categories, difficulty, count)):
            is_long = (i == count - 1)
            ch = generate_and_save_challenge(user, cd, difficulty, is_long)
            created.append(ch)

    # Mark today's batch as generated
    user.daily_challenges_generated = today
    user.save(update_fields=['daily_challenges_generated'])
    return created


def generate_and_save_challenge(user, cd, difficulty, is_long=False):
    """Create a single Challenge from generated data dict."""
    from .challenge_catalog import fix_challenge_link
    cd['_level'] = user.level
    cd = fix_challenge_link(cd)
    link = cd.get('link', '')
    game_key = cd.get('game_key', '')
    ch = Challenge.objects.create(
        user=user,
        category=cd.get('category', 'general'),
        title=cd['title'],
        description=cd['description'],
        xp_reward=cd.get('xp_reward', 50),
        coin_reward=cd.get('coin_reward', 10),
        difficulty=difficulty,
        proof_type=cd.get('proof_type', 'text'),
        is_long=is_long,
        link=link,
        game_key=game_key,
    )
    # Append challenge ID to link for auto-verification (skip for vscode://)
    if link.startswith('vscode://'):
        ch.link = link
    else:
        sep = '&' if '?' in link else '?'
        ch.link = f"{link}{sep}challenge={ch.id}"
    ch.save(update_fields=['link'])
    # Update user's challenge history
    old_history = list(user.challenge_history or [])
    old_history.append(cd['title'])
    user.challenge_history = old_history[-100:]
    user.daily_challenges_generated = date.today()
    user.save(update_fields=['challenge_history', 'daily_challenges_generated'])

    return ch


def _existing_titles(user, today):
    """Return set of challenge titles already generated today."""
    return set(
        Challenge.objects.filter(user=user, created_at=today)
        .values_list('title', flat=True)
    )


def generate_more(user, count=0):
    """Generate additional challenges (free).

    count=0 means "fill up to today's default quota" (legacy behaviour).
    count>0 means "generate exactly this many more" (capped at 20).
    """
    today = date.today()
    categories = user.preferences or ['coding', 'gaming', 'typing', 'reaction', 'cps', 'aim3d', 'memory', 'tictactoe', 'art', 'fitness', 'quiz']
    difficulty = user.difficulty_pref or 'medium'
    history = user.challenge_history or []
    existing_titles = _existing_titles(user, today)

    if count <= 0:
        existing_count = Challenge.objects.filter(user=user, created_at=today, status='pending').count()
        count = max(1, 4 - existing_count)
    else:
        count = min(count, 20)

    created = []

    # Try AI generation
    challenges_data = ai_generate(categories, difficulty, count + 3, history, level=user.level, user=user)
    if challenges_data:
        balanced = balance_categories(challenges_data, categories, user.level)
        ai_titles = {c.get('title') for c in challenges_data}
        fillers = [c for c in balanced if c.get('title') not in ai_titles]
        ai_picks = [c for c in balanced if c.get('title') in ai_titles]

        seen_titles = set(existing_titles)
        deduped = []
        for c in ai_picks:
            t = c.get('title', '')
            if t and t not in seen_titles:
                deduped.append(c)
                seen_titles.add(t)

        slots_for_ai = max(0, count - len(fillers))
        if len(deduped) > slots_for_ai:
            seen_cats = set()
            kept = []
            extras = []
            for c in deduped:
                if c.get('category') in seen_cats or c.get('category') not in categories:
                    extras.append(c)
                else:
                    kept.append(c)
                    seen_cats.add(c.get('category'))
            if len(kept) > slots_for_ai:
                kept = kept[:slots_for_ai]
            if len(kept) < slots_for_ai:
                kept.extend(extras[:slots_for_ai - len(kept)])
            ai_picks = kept
        else:
            ai_picks = deduped

        to_save = fillers + ai_picks
        to_save = to_save[:count]
        for i, cd in enumerate(to_save):
            is_long = (i == len(to_save) - 1) and len(to_save) > 1
            ch = generate_and_save_challenge(user, cd, difficulty, is_long)
            created.append(ch)

    # Catalog fallback
    if not created:
        from .challenge_catalog import get_inapp_challenge, get_poki_challenge, get_offline_challenge, IN_APP_GAMES, POKI_GAMES
        inapp_keys = list(IN_APP_GAMES.keys())
        poki_keys = [g['key'] for g in POKI_GAMES]
        for i in range(count):
            is_long = (i == count - 1)
            picker = random.choice([
                lambda: get_inapp_challenge(random.choice(inapp_keys), user.level),
                lambda: get_poki_challenge(random.choice(poki_keys), user.level),
                lambda: get_offline_challenge(
                    random.choice(categories) if categories else "general",
                    user.level,
                ),
            ])
            cd = picker()
            if cd:
                ch = generate_and_save_challenge(user, cd, difficulty, is_long)
                created.append(ch)

    # Hardcoded fallback
    if not created:
        for i, cd in enumerate(_fallback_challenges(categories, difficulty, count)):
            is_long = (i == count - 1) and count > 1
            ch = generate_and_save_challenge(user, cd, difficulty, is_long)
            created.append(ch)

    return created


def regenerate_challenge(challenge, user):
    """Replace a single challenge. Coin/token cost is handled by the view."""
    categories = user.preferences or ['coding', 'gaming', 'typing', 'reaction', 'cps', 'aim3d', 'memory', 'tictactoe', 'art', 'fitness', 'quiz']
    difficulty = user.difficulty_pref or 'medium'
    history = user.challenge_history or []

    # Try AI first
    data = ai_generate(categories, difficulty, 1, history, level=user.level, user=user)
    if not data:
        # Catalog fallback for reroll
        from .challenge_catalog import (
            get_inapp_challenge, get_poki_challenge, get_offline_challenge,
            IN_APP_GAMES, POKI_GAMES,
        )
        inapp_keys = list(IN_APP_GAMES.keys())
        poki_keys = [g['key'] for g in POKI_GAMES]
        picker = random.choice([
            lambda: get_inapp_challenge(random.choice(inapp_keys), user.level),
            lambda: get_poki_challenge(random.choice(poki_keys), user.level),
            lambda: get_offline_challenge(
                random.choice(categories) if categories else "general",
                user.level,
            ),
        ])
        data = [picker()] if picker() else None
    if not data:
        user.save(update_fields=['coins'])
        return None
    cd = data[0]
    new_ch = generate_and_save_challenge(user, cd, difficulty, is_long=False)
    challenge.status = 'expired'
    challenge.save(update_fields=['status'])
    user.save(update_fields=['coins', 'challenge_history', 'daily_challenges_generated'])
    return new_ch


def _fallback_challenges(categories, difficulty, count=4):
    """Simple fallback if AI fails."""
    import random
    specific_defaults = [
        {"title": "Type 20 WPM in the Typing Test", "description": "Use the ChillX typing test and score 20 WPM. Screenshot your result.", "category": "typing", "game_key": "typing", "proof_type": "image", "xp_reward": 40, "coin_reward": 8, "is_long": False, "link": ""},
        {"title": "Average 350ms Reaction Time", "description": "Take the ChillX reaction time test and average 350ms or faster across 5 attempts. Screenshot.", "category": "reaction", "game_key": "reaction", "proof_type": "image", "xp_reward": 35, "coin_reward": 7, "is_long": False, "link": ""},
        {"title": "Score 500 in Subway Surfers", "description": "Play Subway Surfers on Poki and reach a score of 500. Screenshot your result.", "category": "gaming", "game_key": "poki:subway_surfers", "proof_type": "image", "xp_reward": 25, "coin_reward": 5, "is_long": False, "link": ""},
        {"title": "Build a Simple Calculator", "description": "Create a working calculator using HTML, CSS, and JavaScript. Handle +, -, *, /. Share the code.", "category": "coding", "game_key": "", "proof_type": "text", "xp_reward": 60, "coin_reward": 12, "is_long": False, "link": ""},
        {"title": "Score 6 CPS in Click Speed", "description": "Use the ChillX click speed test and hit 6+ CPS in 10 seconds. Screenshot.", "category": "cps", "game_key": "cps", "proof_type": "image", "xp_reward": 30, "coin_reward": 6, "is_long": False, "link": ""},
        {"title": "Win Tic Tac Toe vs AI", "description": "Play Tic Tac Toe against the ChillX AI and win a game.", "category": "gaming", "game_key": "tictactoe", "proof_type": "text", "xp_reward": 25, "coin_reward": 5, "is_long": False, "link": ""},
        {"title": "Score 1500 in 3D Aim Trainer", "description": "Use the ChillX 3D Aim Trainer and score 1500+ points in 30 seconds.", "category": "gaming", "game_key": "aim3d", "proof_type": "image", "xp_reward": 35, "coin_reward": 7, "is_long": False, "link": ""},
        {"title": "Match 3 pairs in Memory Game", "description": "Play the ChillX Memory Match game and reach level 3.", "category": "gaming", "game_key": "memory", "proof_type": "image", "xp_reward": 30, "coin_reward": 6, "is_long": False, "link": ""},
        {"title": "Run 200m in Endless Runner", "description": "Play the ChillX Endless Runner and cover at least 200 meters.", "category": "gaming", "game_key": "runner", "proof_type": "image", "xp_reward": 30, "coin_reward": 6, "is_long": False, "link": ""},
        {"title": "Draw a Fantasy Character", "description": "Sketch a fantasy character portrait in 30 minutes. Any style. Upload your drawing.", "category": "art", "game_key": "", "proof_type": "image", "xp_reward": 50, "coin_reward": 10, "is_long": False, "link": ""},
        {"title": "15 Pushups Challenge", "description": "Do 15 pushups without stopping. Take a photo after finishing.", "category": "fitness", "game_key": "", "proof_type": "image", "xp_reward": 40, "coin_reward": 8, "is_long": False, "link": ""},
        {"title": "Score 100 in Drift Boss", "description": "Play Drift Boss on Poki and reach 100 points. Screenshot.", "category": "gaming", "game_key": "poki:drift_boss", "proof_type": "image", "xp_reward": 25, "coin_reward": 5, "is_long": False, "link": ""},
        {"title": "Score 2000 in Tunnel Rush", "description": "Play Tunnel Rush on Poki and score 2000+ points. Screenshot.", "category": "gaming", "game_key": "poki:tunnel_rush", "proof_type": "image", "xp_reward": 30, "coin_reward": 6, "is_long": False, "link": ""},
        {"title": "Complete 5 levels in Drive Mad", "description": "Play Drive Mad on Poki and complete 5 levels. Screenshot.", "category": "gaming", "game_key": "poki:drive_mad", "proof_type": "image", "xp_reward": 25, "coin_reward": 5, "is_long": False, "link": ""},
        {"title": "Score 5000 in Tetris", "description": "Play Tetris on Poki and score 5000+ points. Screenshot.", "category": "gaming", "game_key": "poki:tetris", "proof_type": "image", "xp_reward": 30, "coin_reward": 6, "is_long": False, "link": ""},
        {"title": "Reach 256 in 2048", "description": "Play 2048 on Poki and reach the 256 tile. Screenshot.", "category": "gaming", "game_key": "poki:2048", "proof_type": "image", "xp_reward": 25, "coin_reward": 5, "is_long": False, "link": ""},
        {"title": "Win 1 Solitaire game", "description": "Play Solitaire on Poki and win one game. Screenshot.", "category": "gaming", "game_key": "poki:solitaire", "proof_type": "image", "xp_reward": 20, "coin_reward": 4, "is_long": False, "link": ""},
        {"title": "Play a quick game of Tag", "description": "Play Tag on Poki and survive for 60 seconds. Screenshot.", "category": "gaming", "game_key": "poki:tag", "proof_type": "image", "xp_reward": 25, "coin_reward": 5, "is_long": False, "link": ""},
        {"title": "Master Quest", "description": "Spend at least an hour mastering a skill of your choice. Document progress with notes and screenshots.", "category": categories[0] if categories else "general", "game_key": "", "proof_type": "both", "xp_reward": 200, "coin_reward": 40, "is_long": True, "link": ""},
    ]
    random.shuffle(specific_defaults)
    return specific_defaults[:count]
