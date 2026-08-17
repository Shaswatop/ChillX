from datetime import date
from .models import Challenge
from .ai_service import generate_challenges_stream, generate_challenges as ai_generate


# Gets today's pending challenges that already exist.
# If removed, views can't show today's challenges.
# Used by the daily challenge views.
def get_todays_challenges(user):
    today = date.today()
    return list(Challenge.objects.filter(
        user=user,
        created_at=today,
        status='pending'
    ))


# Generates today's batch of challenges on first visit of the day.
# If removed, daily challenges never get created.
# Called when the dashboard loads.
def auto_generate_daily(user):
    today = date.today()
    if user.daily_challenges_generated == today:
        return []

    count = user.daily_challenge_count or 3
    categories = user.preferences or [
        'coding', 'gaming', 'typing', 'reaction', 'cps',
        'art', 'fitness', 'quiz',
    ]
    difficulty = user.difficulty_pref or 'medium'
    history = user.challenge_history or []

    # ask the AI for the whole batch
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

    # drop duplicate titles, keep one per picked category
    seen_titles = set()
    seen_cats = set()
    to_save = []
    for c in streamed:
        title = c.get('title', '')
        cat = c.get('category', '')
        if not title or title in seen_titles:
            continue
        if cat in seen_cats or (categories and cat not in categories):
            continue
        seen_titles.add(title)
        seen_cats.add(cat)
        to_save.append(c)
        if len(to_save) >= count:
            break

    for i, cd in enumerate(to_save):
        is_long = (i == len(to_save) - 1) and len(to_save) > 1
        ch = generate_and_save_challenge(user, cd, difficulty, is_long)
        created.append(ch)

    # mark today's batch as generated
    user.daily_challenges_generated = today
    user.save(update_fields=['daily_challenges_generated'])
    return created


# Saves one challenge row from a data dict and adds its id to the link.
# If removed, no challenges get saved to the database.
# Used by every generator in this file.
def generate_and_save_challenge(user, cd, difficulty, is_long=False):
    from urllib.parse import parse_qs, urlparse
    from .challenge_catalog import fix_challenge_link
    from .game_capabilities import GAME_CAPABILITIES, validate_challenge
    cd['_level'] = user.level
    cd = fix_challenge_link(cd)
    link = cd.get('link', '')
    game_key = cd.get('game_key', '')

    # Pull the scaled target (and fitness mode) out of the built game link so
    # the level-scaled target is authoritative and the database always agrees
    # with the link the game actually loads. Overwrites any AI-suggested target
    # so title/objective/target never drift from what the user verifies against.
    query = parse_qs(urlparse(link).query)
    if game_key in GAME_CAPABILITIES:
        raw = (query.get('target') or [None])[0]
        try:
            cd['target'] = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            cd['target'] = None
        if game_key == 'fitness':
            mode = (query.get('mode') or ['reps'])[0]
            if mode in ('time', 'distance', 'reps'):
                cd.setdefault('metric', mode)

    cleaned, _problems = validate_challenge(cd)

    ch = Challenge.objects.create(
        user=user,
        category=cleaned.get('category', 'general'),
        title=cleaned['title'],
        description=cleaned['description'],
        xp_reward=cleaned.get('xp_reward', 50),
        coin_reward=cleaned.get('coin_reward', 10),
        difficulty=difficulty,
        proof_type=cleaned.get('proof_type', 'text'),
        is_long=is_long,
        link=link,
        game_key=game_key,
        objective=(cleaned.get('objective') or '')[:200],
        metric=(cleaned.get('metric') or '')[:50],
        target=cleaned.get('target'),
        unit=(cleaned.get('unit') or '')[:20],
        estimated_duration=(cleaned.get('estimated_duration') or '')[:50],
        special_condition=(cleaned.get('special_condition') or '')[:1000],
        ai_meta=cleaned,
    )
    # add the challenge id to the link so results can be verified
    # (skip this for empty links so we never produce a broken relative URL)
    if link:
        sep = '?'
        if '?' in link:
            sep = '&'
        ch.link = f"{link}{sep}challenge={ch.id}"
    else:
        ch.link = ""
    ch.save(update_fields=['link'])
    # save the title in the user's history
    old_history = list(user.challenge_history or [])
    old_history.append(cd['title'])
    user.challenge_history = old_history[-100:]
    user.daily_challenges_generated = date.today()
    user.save(update_fields=['challenge_history', 'daily_challenges_generated'])

    return ch


# Returns the set of titles already made for today.
# If removed, generate_more can't skip duplicate titles.
# Used in generate_more.
def _existing_titles(user, today):
    return set(
        Challenge.objects.filter(user=user, created_at=today)
        .values_list('title', flat=True)
    )


# Generates extra challenges when the user asks for more.
# If removed, the get-more-challenges button does nothing.
# Used by the generate-more view.
def generate_more(user, count=0):
    today = date.today()
    categories = user.preferences or ['coding', 'gaming', 'typing', 'reaction', 'cps', 'aim3d', 'memory', 'tictactoe', 'art', 'fitness', 'quiz']
    difficulty = user.difficulty_pref or 'medium'
    history = user.challenge_history or []
    existing_titles = _existing_titles(user, today)

    if count <= 0:
        existing_count = Challenge.objects.filter(user=user, created_at=today, status='pending').count()
        count = 4 - existing_count
        if count < 1:
            count = 1
    else:
        if count > 20:
            count = 20

    created = []
    data = ai_generate(categories, difficulty, count + 3, history, level=user.level, user=user)
    if not data:
        return created

    # keep only fresh titles, one per category, up to the requested count
    seen_titles = set(existing_titles)
    seen_cats = set()
    to_save = []
    for c in data:
        title = c.get('title', '')
        cat = c.get('category', '')
        if not title or title in seen_titles:
            continue
        if cat in seen_cats or (categories and cat not in categories):
            continue
        seen_titles.add(title)
        seen_cats.add(cat)
        to_save.append(c)
        if len(to_save) >= count:
            break

    for i, cd in enumerate(to_save):
        is_long = (i == len(to_save) - 1) and len(to_save) > 1
        ch = generate_and_save_challenge(user, cd, difficulty, is_long)
        created.append(ch)

    return created


# Replaces one challenge with a fresh one for rerolls.
# If removed, rerolling a challenge stops working.
# Used by the reroll view.
def regenerate_challenge(challenge, user):
    categories = user.preferences or ['coding', 'gaming', 'typing', 'reaction', 'cps', 'aim3d', 'memory', 'tictactoe', 'art', 'fitness', 'quiz']
    difficulty = user.difficulty_pref or 'medium'
    history = user.challenge_history or []

    # ask the AI for a brand new one
    data = ai_generate(categories, difficulty, 1, history, level=user.level, user=user)
    if not data:
        user.save(update_fields=['coins'])
        return None
    cd = data[0]
    new_ch = generate_and_save_challenge(user, cd, difficulty, is_long=False)
    challenge.status = 'expired'
    challenge.save(update_fields=['status'])
    user.save(update_fields=['coins', 'challenge_history', 'daily_challenges_generated'])
    return new_ch
