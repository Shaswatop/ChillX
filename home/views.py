import json
import random
import string
import time
from datetime import date, timedelta
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.db.models import Q, Count
from django.core.cache import cache
from .models import Challenge, Message, FriendRequest
from .consumers import generate_room_code, get_rank
from .achievement_views import get_level_from_xp, get_tier_for_xp, get_xp_for_level
from .ai_service import chat_response, _groq_request, _gemini_request, _openrouter_request
User = get_user_model()


# Shows the signup page and creates a new user account on POST.
# If removed, /signup/ will 404 and new users cant register.
# Change the route in home/urls.py (name='signup') or signup.html.
def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if password != password2:
            return render(request, 'signup.html', {'error': "Passwords don't match"})
        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email already exists'})
        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect('onboarding')
    return render(request, 'signup.html')


# Shows the signin page and logs the user in on POST.
# If removed, /signin/ will 404 and nobody can log in.
# Change the route in home/urls.py (name='signin') or signin.html.
def signin_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            # Skip onboarding if already completed
            if user.preferences:
                if user.display_name:
                    return redirect('dashboard')
                return redirect('create_profile')
            return redirect('onboarding')
        else:
            return render(request, 'signin.html', {'error': 'Invalid email or password'})
    return render(request, 'signin.html')


# Logs out the current user and sends them back to signin.
# If removed, /logout/ will 404 and users cant sign out.
# Change the route in home/urls.py (name='logout').
def logout_view(request):
    logout(request)
    return redirect('signin')


# Old /chillx/ url that just points to the dashboard now.
# If removed, /chillx/ will 404 (used by old links).
# Change the route in home/urls.py (name='chillx').
def chillx_view(request):
    return redirect('dashboard')
# Categories shown in onboarding and used as post/filter categories on the social page.
CATEGORIES = [
    {'id': 'coding', 'name': 'Coding', 'icon': 'fa-solid fa-code'},
    {'id': 'art', 'name': 'Art & Design', 'icon': 'fa-solid fa-palette'},
    {'id': 'gaming', 'name': 'Gaming', 'icon': 'fa-solid fa-gamepad'},
    {'id': 'typing', 'name': 'Typing Speed', 'icon': 'fa-solid fa-keyboard'},
    {'id': 'reaction', 'name': 'Reaction Time', 'icon': 'fa-solid fa-bolt'},
    {'id': 'cps', 'name': 'CPS (Clicks)', 'icon': 'fa-solid fa-mouse-pointer'},
    {'id': 'fitness', 'name': 'Fitness', 'icon': 'fa-solid fa-dumbbell'},
    {'id': 'quiz', 'name': 'Quiz & Trivia', 'icon': 'fa-solid fa-question-circle'},
]


# Lets new users pick their favourite categories after signup.
# If removed, /onboarding/ 404s and new signups get stuck.
# Change the route in home/urls.py (name='onboarding') or onboarding.html.
@login_required
def onboarding_view(request):
    if request.user.preferences:
        if not request.user.display_name:
            return redirect('create_profile')
        return redirect('dashboard')
    if request.method == 'POST':
        cats = request.POST.getlist('categories')
        request.user.preferences = cats
        request.user.save(update_fields=['preferences'])
        return redirect('create_profile')
    return render(request, 'onboarding.html', {'categories': CATEGORIES})


# Lets the user set their display name, bio and avatar after onboarding.
# If removed, /create-profile/ 404s and new users never finish setup.
# Change the route in home/urls.py (name='create_profile') or create_profile.html.
@login_required
def create_profile_view(request):
    if request.user.display_name:
        return redirect('dashboard')
    if request.method == 'POST':
        name = request.POST.get('display_name', '').strip()
        if len(name) < 3:
            return render(request, 'create_profile.html', {'error': 'Name must be at least 3 characters'})
        request.user.display_name = name
        request.user.bio = request.POST.get('bio', '').strip()
        avatar_b64 = request.POST.get('avatar_base64', '')
        if ',' in avatar_b64:
            avatar_b64 = avatar_b64.split(',')[1]
        if avatar_b64:
            request.user.avatar_base64 = avatar_b64
        request.user.save(update_fields=['display_name', 'bio', 'avatar_base64'])
        return redirect(reverse('dashboard') + '?welcomed=1')
    return render(request, 'create_profile.html')


# Main dashboard page - shows coins, xp, level and recent game stats.
# If removed, /dashboard/ 404s and the whole app is unusable.
# Change the route in home/urls.py (name='dashboard') or dashboard/home.html.
@login_required
def dashboard_view(request):
    from .models import UserGameStats
    user = request.user
    xp = user.xp
    level = user.level
    coins = user.coins
    xp_in_current = xp - (level - 1) * 1000
    xp_next_level = 1000
    if xp_next_level > 0:
        progress = int(xp_in_current / xp_next_level * 100)
    else:
        progress = 0
    if progress > 100:
        progress = 100
    game_stats = UserGameStats.objects.filter(user=user).order_by('-last_played')[:8]
    titles = {
        'runner': 'Super Mario Runner', 'typing': 'Typing Rush',
        'reaction': 'Reaction Shot', 'cps': 'CPS Slam',
        'memory': 'Memory Matrix', 'tictactoe': 'Tic Tac Toe',
        'aim3d': 'Aim 3D', 'fitness': 'Fitness', 'quiz': 'Quiz',
    }
    stats_data = []
    for gs in game_stats:
        stats_data.append({
            'game': titles.get(gs.game, gs.game),
            'key': gs.game,
            'best_score': gs.best_score,
            'best_score_secondary': gs.best_score_secondary,
            'plays': gs.plays,
        })
    context = {
        'player': {
            'coins': coins,
            'xp': xp,
            'level': level,
            'xp_progress': progress,
            'xp_next': xp_next_level,
            'xp_current': xp_in_current,
            'diamonds': user.diamonds,
            'rice': '0',
            'quests': '0',
        },
        'user': user,
        'game_stats': stats_data,
        'show_welcome': request.GET.get('welcomed') == '1',
    }
    return render(request, 'dashboard/home.html', context)
# Title options for the settings page dropdown.
TITLES = [
    {'id': '', 'name': 'None'},
    {'id': 'arena_champion', 'name': 'The Arena Champion'},
    {'id': 'code_warrior', 'name': 'Code Warrior'},
    {'id': 'shadow_artisan', 'name': 'Shadow Artisan'},
    {'id': 'crystal_guardian', 'name': 'Crystal Guardian'},
    {'id': 'void_walker', 'name': 'Void Walker'},
    {'id': 'emerald_archer', 'name': 'Emerald Archer'},
    {'id': 'frost_mage', 'name': 'Frost Mage'},
    {'id': 'iron_colossus', 'name': 'Iron Colossus'},
    {'id': 'phantom_blade', 'name': 'Phantom Blade'},
    {'id': 'star_seer', 'name': 'Star Seer'},
]
# Theme options (colors) for the settings page.
THEMES = [
    {'id': 'dark-purple', 'name': 'Dark Purple', 'color': 'linear-gradient(135deg,#2d1b4e,#1a0a2e)'},
    {'id': 'crimson', 'name': 'Crimson', 'color': 'linear-gradient(135deg,#4e1b1b,#2e0a0a)'},
    {'id': 'emerald', 'name': 'Emerald', 'color': 'linear-gradient(135deg,#1b4e2d,#0a2e1a)'},
    {'id': 'sapphire', 'name': 'Sapphire', 'color': 'linear-gradient(135deg,#1b2d4e,#0a1a2e)'},
    {'id': 'golden', 'name': 'Golden', 'color': 'linear-gradient(135deg,#4e3e1b,#2e240a)'},
    {'id': 'void', 'name': 'Void', 'color': 'linear-gradient(135deg,#0a0a0a,#1a1a2e)'},
]
# Avatar frame options for the settings page.
FRAMES = [
    {'id': 'none', 'name': 'None'},
    {'id': 'golden_crown', 'name': 'Golden Crown'},
    {'id': 'crystal_spikes', 'name': 'Crystal Spikes'},
    {'id': 'shadow_flame', 'name': 'Shadow Flame'},
    {'id': 'runic_circle', 'name': 'Runic Circle'},
    {'id': 'frost_ring', 'name': 'Frost Ring'},
    {'id': 'void_echo', 'name': 'Void Echo'},
]
# Groq model options for the AI companion settings.
GROQ_MODELS = [
    {'id': 'llama-3.3-70b-versatile', 'name': 'Llama 3.3 70B'},
    {'id': 'llama3-8b-8192', 'name': 'Llama 3 8B'},
    {'id': 'mixtral-8x7b-32768', 'name': 'Mixtral 8x7B'},
    {'id': 'gemma2-9b-it', 'name': 'Gemma 2 9B'},
    {'id': 'gemma-7b-it', 'name': 'Gemma 7B'},
    {'id': 'llama-3.1-70b-versatile', 'name': 'Llama 3.1 70B'},
    {'id': 'llama-3.1-8b-instant', 'name': 'Llama 3.1 8B'},
    {'id': 'llama-guard-3-8b', 'name': 'Llama Guard 3 8B'},
    {'id': 'llama3-groq-70b-8192-tool-use-preview', 'name': 'Groq Llama 3 70B Tool'},
    {'id': 'llama3-groq-8b-8192-tool-use-preview', 'name': 'Groq Llama 3 8B Tool'},
]
GEMINI_MODELS = [
    {'id': 'gemini-2.0-flash', 'name': 'Gemini 2.0 Flash'},
    {'id': 'gemini-2.0-flash-lite', 'name': 'Gemini 2.0 Flash Lite'},
    {'id': 'gemini-1.5-flash', 'name': 'Gemini 1.5 Flash'},
    {'id': 'gemini-1.5-pro', 'name': 'Gemini 1.5 Pro'},
    {'id': 'gemini-2.0-pro-exp', 'name': 'Gemini 2.0 Pro (Exp)'},
]
# Gemini model options for the AI companion settings.
SETTINGS_CONTEXT = {
    'categories': CATEGORIES,
    'titles': TITLES,
    'themes': THEMES,
    'frames': FRAMES,
    'groq_models': GROQ_MODELS,
    'gemini_models': GEMINI_MODELS,
}


# Builds the player context dict (coins, xp, level, game stats) for templates.
# If removed, settings page and dashboard break since they call it.
# Called from settings_view and the dashboard views, no direct url.
def _player_context(user):
    from .models import UserGameStats
    xp = user.xp
    level = user.level
    coins = user.coins
    xp_in_current = xp - (level - 1) * 1000
    xp_next_level = 1000
    if xp_next_level > 0:
        progress = int(xp_in_current / xp_next_level * 100)
    else:
        progress = 0
    if progress > 100:
        progress = 100
    game_stats = UserGameStats.objects.filter(user=user).order_by('-last_played')[:8]
    titles = {
        'runner': 'Super Mario Runner', 'typing': 'Typing Rush',
        'reaction': 'Reaction Shot', 'cps': 'CPS Slam',
        'memory': 'Memory Matrix', 'tictactoe': 'Tic Tac Toe',
        'aim3d': 'Aim 3D', 'fitness': 'Fitness', 'quiz': 'Quiz',
    }
    stats_data = []
    for gs in game_stats:
        stats_data.append({
            'game': titles.get(gs.game, gs.game),
            'key': gs.game,
            'best_score': gs.best_score,
            'best_score_secondary': gs.best_score_secondary,
            'plays': gs.plays,
        })
    return {
        'player': {
            'coins': coins,
            'xp': xp,
            'level': level,
            'xp_progress': progress,
            'xp_next': xp_next_level,
            'xp_current': xp_in_current,
            'diamonds': user.diamonds,
            'rice': '0',
            'quests': '0',
        },
        'game_stats': stats_data,
    }


# Settings page - edits profile, passwords, api keys, account reset/delete.
# If removed, /settings/ 404s and users cant change their settings.
# Change the route in home/urls.py (name='settings') or dashboard/settings.html.
@login_required
def settings_view(request):
    if request.method == 'POST':
        user = request.user
        # Danger zone: reset progress
        if request.POST.get('reset_progress'):
            user.xp_boosts = 0
            user.rerolls = 0
            user.streak_freezes = 0
            user.contracts = []
            user.preferences = []
            user.save()
            ctx = dict(SETTINGS_CONTEXT, success='Progress has been reset.', user_prefs=[], **_player_context(user))
            return render(request, 'dashboard/settings.html', ctx)
        # Danger zone: delete account
        if request.POST.get('delete_account'):
            user.delete()
            logout(request)
            return redirect('signup')
        # Account Settings
        uname = request.POST.get('username', '').strip()
        if uname and User.objects.exclude(pk=user.pk).filter(username=uname).exists():
            ctx = dict(SETTINGS_CONTEXT, error='Username already taken.', user_prefs=user.preferences or [], **_player_context(user))
            return render(request, 'dashboard/settings.html', ctx)
        if uname:
            user.username = uname
        email = request.POST.get('email', '').strip()
        if email and User.objects.exclude(pk=user.pk).filter(email=email).exists():
            ctx = dict(SETTINGS_CONTEXT, error='Email already in use.', user_prefs=user.preferences or [], **_player_context(user))
            return render(request, 'dashboard/settings.html', ctx)
        if email:
            user.email = email
        name = request.POST.get('display_name', '').strip()
        if len(name) >= 3:
            user.display_name = name
        user.bio = request.POST.get('bio', '').strip()
        avatar_b64 = request.POST.get('avatar_base64', '').strip()
        if ',' in avatar_b64:
            avatar_b64 = avatar_b64.split(',')[1]
        if avatar_b64:
            user.avatar_base64 = avatar_b64
        # Profile & Personalization
        user.title = request.POST.get('title', '')
        user.theme = request.POST.get('theme', 'dark-purple')
        user.avatar_frame = request.POST.get('avatar_frame', 'none')
        # Challenge Preferences
        prefs = request.POST.getlist('preferences')
        if prefs:
            user.preferences = prefs
        user.difficulty_pref = request.POST.get('difficulty_pref', 'medium')
        user.daily_challenge_count = int(request.POST.get('daily_challenge_count', 3))
        # Notifications
        user.notify_xp = request.POST.get('notify_xp') == 'on'
        user.notify_badges = request.POST.get('notify_badges') == 'on'
        user.notify_friend_activity = request.POST.get('notify_friend_activity') == 'on'
        user.notify_leaderboard = request.POST.get('notify_leaderboard') == 'on'
        user.notify_streak = request.POST.get('notify_streak') == 'on'
        # Privacy & Social
        user.profile_visibility = request.POST.get('profile_visibility', 'public')
        user.who_can_follow = request.POST.get('who_can_follow', 'everyone')
        # Accountability Contract
        contract_rule = request.POST.get('contract_rule', '').strip()
        contract_penalty = request.POST.get('contract_penalty', '').strip()
        if contract_rule:
            contracts = list(user.contracts or [])
            contracts.append({'name': contract_rule, 'penalty': f"{contract_penalty} coins" if contract_penalty else '', 'description': ''})
            user.contracts = contracts
        # AI Companion
        user.ai_name = request.POST.get('ai_name', 'ChillX').strip() or 'ChillX'
        ai_avatar = request.POST.get('ai_avatar_base64', '').strip()
        if ai_avatar:
            user.ai_avatar_base64 = ai_avatar
        user.ai_personality = request.POST.get('ai_personality', '').strip()
        user.groq_api_key = request.POST.get('groq_api_key', '').strip()
        user.gemini_api_key = request.POST.get('gemini_api_key', '').strip()
        user.openrouter_api_key = request.POST.get('openrouter_api_key', '').strip()
        user.groq_model = request.POST.get('groq_model', 'llama-3.3-70b-versatile')
        user.gemini_model = request.POST.get('gemini_model', 'gemini-1.5-flash')
        user.openrouter_model = request.POST.get('openrouter_model', 'openai/gpt-4o-mini')
        # Password change
        cp = request.POST.get('current_password', '')
        np = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')
        if cp or np or confirm:
            if not user.check_password(cp):
                ctx = dict(SETTINGS_CONTEXT, error='Current password is incorrect.', user_prefs=user.preferences or [], **_player_context(user))
                return render(request, 'dashboard/settings.html', ctx)
            if not np:
                ctx = dict(SETTINGS_CONTEXT, error='New password is required.', user_prefs=user.preferences or [], **_player_context(user))
                return render(request, 'dashboard/settings.html', ctx)
            if np != confirm:
                ctx = dict(SETTINGS_CONTEXT, error='New passwords do not match.', user_prefs=user.preferences or [], **_player_context(user))
                return render(request, 'dashboard/settings.html', ctx)
            if len(np) < 6:
                ctx = dict(SETTINGS_CONTEXT, error='New password must be at least 6 characters.', user_prefs=user.preferences or [], **_player_context(user))
                return render(request, 'dashboard/settings.html', ctx)
            user.set_password(np)
        user.save()
        if cp or np or confirm:
            update_session_auth_hash(request, user)
        ctx = dict(SETTINGS_CONTEXT, success='All changes saved successfully.', user_prefs=user.preferences or [], **_player_context(user))
        return render(request, 'dashboard/settings.html', ctx)
    ctx = dict(SETTINGS_CONTEXT, user_prefs=request.user.preferences or [], **_player_context(request.user))
    return render(request, 'dashboard/settings.html', ctx)


# Root url - just sends logged in users to dashboard, others to signin.
# If removed, / 404s so nothing loads at the base url.
# Change the route in home/urls.py (name='home').
def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('signin')


# Shows todays challenges and auto-generates a fresh batch each day.
# If removed, /challenges/ 404s and nobody can see daily challenges.
# Change the route in home/urls.py (name='challenges') or challenges.html.
@login_required
def challenges_view(request):
    from .challenge_gen import get_todays_challenges, auto_generate_daily
    from .user_performance import get_streak
    from django.core.cache import cache
    import threading
    today = date.today()
    user = request.user
    generating = False
    # Auto-generate today's challenges on first visit of the day.
    # This used to BLOCK the page for ~25s (Groq AI call) — now it runs in a
    # background thread so the page renders instantly and shows a "Generating…"
    # state that auto-reloads when the batch is ready. A cache flag makes sure
    # concurrent requests don't all fire a second generation.
    try:
        lock_key = 'chgen_%s_%s' % (user.id, today.isoformat())
        if user.daily_challenges_generated != today:
            if not cache.get(lock_key):
                cache.set(lock_key, True, 600)
                generating = True

                def _generate():
                    from django.db import close_old_connections
                    try:
                        close_old_connections()
                        from django.contrib.auth import get_user_model
                        fresh = get_user_model().objects.get(id=user.id)
                        auto_generate_daily(fresh)
                    except Exception:
                        pass
                    finally:
                        try:
                            cache.delete(lock_key)
                        except Exception:
                            pass
                        close_old_connections()

                threading.Thread(target=_generate, daemon=True).start()
            else:
                generating = True
    except Exception:
        # Never let generation failure block the page render
        pass
    challenges = get_todays_challenges(user)
    completed_today = user.challenges.filter(created_at=today, status='completed').count()
    pending_count = 0
    submitted_count = 0
    for c in challenges:
        if c.status == 'pending':
            pending_count += 1
        elif c.status == 'submitted':
            submitted_count += 1
    streak = get_streak(user)
    return render(request, 'challenges.html', {
        'challenges': challenges,
        'generating': generating,
        'pending_count': pending_count,
        'completed_count': completed_today,
        'submitted_count': submitted_count,
        'total_count': len(challenges),
        'streak': streak,
        'user_coins': user.coins,
        'user_rerolls': user.rerolls,
        'daily_free_available': user.rerolls == 0 and user.last_free_reroll_date != today,
        'user_xp': user.xp,
        'user_level': user.level,
        'user': user,
        'today': today,
    })


# Handles a submitted challenge - checks proof with AI, awards xp/coins.
# If removed, submitting any challenge breaks and users lose rewards.
# Change the route in home/urls.py (name='challenge_submit').
@login_required
def challenge_submit(request, challenge_id):
    from .ai_service import check_submission_text, check_submission_image, check_submission_code
    from .rewards import finalize_challenge
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return redirect('challenges')
    if request.method == 'POST':
        proof_text = request.POST.get('proof_text', '').strip()
        proof_image = request.POST.get('proof_image', '').strip()
        proof_code = request.POST.get('proof_code', '').strip()
        # AI check: try image first, fall back to text if image AI fails
        target = challenge.target
        unit = challenge.unit or ""
        objective = challenge.objective or ""
        cat_l = (challenge.category or '').lower()
        if proof_code and ('cod' in cat_l or 'program' in cat_l or 'develop' in cat_l or 'script' in cat_l):
            # Coding challenge — the AI checks the pasted code and gives hints
            result = check_submission_code(challenge.title, challenge.description, proof_code, objective)
        elif challenge.proof_type == 'image' and proof_image:
            result = check_submission_image(challenge.title, challenge.description, proof_image, target, unit, objective)
            # If image AI is unavailable, try the text check as a backup
            if not result.get('passed') and result.get('score', 0) <= 2 and 'unavailable' in result.get('feedback', '') and proof_text:
                result = check_submission_text(challenge.title, challenge.description, proof_text, target, unit, objective)
        else:
            result = check_submission_text(challenge.title, challenge.description, proof_text, target, unit, objective)
        score = result.get('score', 7)
        feedback = result.get('feedback', 'Well done!')
        passed = result.get('passed', score >= 5)
        challenge.proof_text = proof_code or proof_text
        challenge.proof_image = proof_image
        challenge.quality_score = score
        challenge.feedback = feedback
        challenge.ai_checked = True
        rw = finalize_challenge(request.user, challenge, passed)
        from django.http import JsonResponse
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Saves/updates a users game stats (best score, plays) in one place.
# If removed, game stats stop updating everywhere (used by verify_* views).
# Called from the verify_* views, no direct url.
def _save_game_stats_sync(user, game, score, score_secondary=0, deaths=0):
    from .models import UserGameStats
    from django.utils import timezone
    stats, _ = UserGameStats.objects.get_or_create(user=user, game=game)
    stats.plays += 1
    if score > stats.best_score:
        stats.best_score = int(score)
    if score_secondary > stats.best_score_secondary:
        stats.best_score_secondary = int(score_secondary)
    if game == 'runner':
        stats.deaths += deaths
    stats.last_played = timezone.now()
    stats.save()


# Checks a CPS challenge result and gives xp/coins if it passed.
# If removed, the cps game cannot submit its score to the challenge.
# Change the route in home/urls.py (name='verify_cps').
@login_required
def verify_cps(request):
    from django.http import JsonResponse
    from .models import Challenge
    from .rewards import finalize_challenge
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    challenge_id = request.POST.get("challenge_id")
    score = float(request.POST.get("score", 0))
    target = float(request.POST.get("target", 0))
    clicks = int(request.POST.get("clicks", 0))
    seconds = int(request.POST.get("time", 10))
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    passed = score >= target
    quality = score / target * 10
    if quality > 10:
        quality = 10
    challenge.quality_score = int(quality)
    challenge.feedback = f"CPS: {score}/{target} ({clicks} clicks in {seconds}s)"
    challenge.proof_text = f"CPS: {score} in {seconds}s"
    challenge.ai_checked = True
    rw = finalize_challenge(request.user, challenge, passed)
    _save_game_stats_sync(request.user, 'cps', score, clicks)
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Checks a reaction time challenge result and rewards the user.
# If removed, the reaction game cannot submit its score.
# Change the route in home/urls.py (name='verify_reaction').
@login_required
def verify_reaction(request):
    from django.http import JsonResponse
    from .models import Challenge
    from .rewards import finalize_challenge
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    challenge_id = request.POST.get("challenge_id")
    avg = float(request.POST.get("avg", 0))
    target = float(request.POST.get("target", 0))
    best = int(request.POST.get("best", 0))
    attempts = int(request.POST.get("attempts", 0))
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    passed = avg <= target
    if target > 1:
        denom = target
    else:
        denom = 1
    if avg <= target:
        # Beat the target — score scales up as they get faster (5 minimum for a pass)
        quality = 5 + int(5 * (1 - (avg / denom)))
    else:
        # Missed it — score drops below 5 as the gap grows
        quality = 10 - int((avg / denom) * 10)
    if quality < 1:
        quality = 1
    if quality > 10:
        quality = 10
    challenge.quality_score = int(quality)
    challenge.feedback = f"Reaction: {avg}/{target}ms avg, best {best}ms ({attempts} attempts)"
    challenge.proof_text = f"Reaction: {avg}ms avg in {attempts} attempts"
    challenge.ai_checked = True
    rw = finalize_challenge(request.user, challenge, passed)
    _save_game_stats_sync(request.user, 'reaction', best, attempts)
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Checks a typing challenge result and rewards the user.
# If removed, the typing game cannot submit its wpm score.
# Change the route in home/urls.py (name='verify_typing').
@login_required
def verify_typing(request):
    from django.http import JsonResponse
    from .models import Challenge
    from .rewards import finalize_challenge
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    challenge_id = request.POST.get("challenge_id")
    score = float(request.POST.get("score", 0))
    target = float(request.POST.get("target", 0))
    accuracy = int(request.POST.get("accuracy", 100))
    words = int(request.POST.get("words", 0))
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    passed = score >= target
    if target > 1:
        denom = target
    else:
        denom = 1
    quality = score / denom * 10
    if quality > 10:
        quality = 10
    challenge.quality_score = int(quality)
    challenge.feedback = f"Typing: {score}/{target} WPM ({accuracy}% accuracy)"
    challenge.proof_text = f"Typing: {score} WPM, {words} words, {accuracy}% accuracy"
    challenge.ai_checked = True
    rw = finalize_challenge(request.user, challenge, passed)
    _save_game_stats_sync(request.user, 'typing', score, accuracy)
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Checks a memory challenge result and rewards the user.
# If removed, the memory game cannot submit its score.
# Change the route in home/urls.py (name='verify_memory').
@login_required
def verify_memory(request):
    from django.http import JsonResponse
    from .models import Challenge
    from .rewards import finalize_challenge
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    challenge_id = request.POST.get("challenge_id")
    score = int(request.POST.get("score", 0))
    target = int(request.POST.get("target", 0))
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    passed = score >= target
    if target > 1:
        denom = target
    else:
        denom = 1
    quality = score / denom * 10
    if quality > 10:
        quality = 10
    challenge.quality_score = int(quality)
    challenge.feedback = f"Memory: level {score}/{target}"
    challenge.proof_text = f"Memory: level {score}"
    challenge.ai_checked = True
    rw = finalize_challenge(request.user, challenge, passed)
    _save_game_stats_sync(request.user, 'memory', score)
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Checks a runner game challenge result and rewards the user.
# If removed, the runner game cannot submit its score.
# Change the route in home/urls.py (name='verify_runner').
@login_required
def verify_runner(request):
    from django.http import JsonResponse
    from .models import Challenge
    from .rewards import finalize_challenge
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    challenge_id = request.POST.get("challenge_id")
    score = int(request.POST.get("score", 0))
    target = int(request.POST.get("target", 0))
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    passed = score >= target
    if target > 1:
        denom = target
    else:
        denom = 1
    quality = score / denom * 10
    if quality > 10:
        quality = 10
    challenge.quality_score = int(quality)
    challenge.feedback = f"Runner: {score}/{target} points"
    challenge.proof_text = f"Runner: {score} points"
    challenge.ai_checked = True
    rw = finalize_challenge(request.user, challenge, passed)
    _save_game_stats_sync(request.user, 'runner', score)
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Checks a tictactoe challenge result (win or loss) and rewards.
# If removed, tictactoe cannot submit its result.
# Change the route in home/urls.py (name='verify_tictactoe').
@login_required
def verify_tictactoe(request):
    from django.http import JsonResponse
    from .models import Challenge
    from .rewards import finalize_challenge
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    challenge_id = request.POST.get("challenge_id")
    won = request.POST.get("won") == 'true'
    wins = int(request.POST.get("wins", 0))
    losses = int(request.POST.get("losses", 0))
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    passed = won
    if won:
        challenge.quality_score = 10
        result_word = 'Won'
    else:
        challenge.quality_score = 0
        result_word = 'Lost'
    challenge.feedback = f"TicTacToe: {result_word} (session: {wins}W/{losses}L)"
    challenge.proof_text = f"TicTacToe: {result_word}"
    challenge.ai_checked = True
    rw = finalize_challenge(request.user, challenge, passed)
    _save_game_stats_sync(request.user, 'tictactoe', wins)
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Checks an aim3d challenge result and rewards the user.
# If removed, the aim3d game cannot submit its score.
# Change the route in home/urls.py (name='verify_aim3d').
@login_required
def verify_aim3d(request):
    from django.http import JsonResponse
    from .models import Challenge
    from .rewards import finalize_challenge
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    challenge_id = request.POST.get("challenge_id")
    score = int(request.POST.get("score", 0))
    target = int(request.POST.get("target", 0))
    accuracy = request.POST.get("accuracy", "0%")
    hits = int(request.POST.get("hits", 0))
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    passed = score >= target
    if target:
        quality = score / target * 10
        if quality > 10:
            quality = 10
        challenge.quality_score = int(quality)
    else:
        challenge.quality_score = 5
    challenge.feedback = f"Aim3D: {score}/{target} pts ({accuracy}, {hits} hits)"
    challenge.proof_text = f"Aim3D: {score} pts"
    challenge.ai_checked = True
    rw = finalize_challenge(request.user, challenge, passed)
    _save_game_stats_sync(request.user, 'aim3d', score, hits)
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Checks a fitness challenge result and rewards the user.
# If removed, fitness challenges cannot be submitted.
# Change the route in home/urls.py (name='verify_fitness').
@login_required
def verify_fitness(request):
    from django.http import JsonResponse
    from .models import Challenge
    from .rewards import finalize_challenge
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    challenge_id = request.POST.get("challenge_id")
    exercise = request.POST.get("exercise", "exercise")
    target = float(request.POST.get("target", 0))
    actual = float(request.POST.get("actual", 0))
    mode = request.POST.get("mode", "reps")
    if not challenge_id:
        return JsonResponse({"error": "challenge_id required"}, status=400)
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    if challenge.game_key != 'fitness':
        return JsonResponse({"error": "Not a fitness challenge"}, status=400)
    passed = actual >= target
    if target > 0.1:
        denom = target
    else:
        denom = 0.1
    pct = actual / denom * 10
    if pct > 10:
        pct = 10
    pct = int(pct)
    challenge.quality_score = pct
    mode_label = {"reps": "reps", "time": "sec", "distance": "km"}.get(mode, "")
    challenge.feedback = f"Fitness: {exercise} {int(actual)}{mode_label}/{int(target)}{mode_label}"
    challenge.proof_text = f"Fitness: {exercise} {int(actual)}{mode_label}"
    challenge.ai_checked = True
    rw = finalize_challenge(request.user, challenge, passed)
    _save_game_stats_sync(request.user, 'fitness', actual)
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Checks a quiz challenge result and rewards the user.
# If removed, quiz challenges cannot be submitted.
# Change the route in home/urls.py (name='verify_quiz').
@login_required
def verify_quiz(request):
    from django.http import JsonResponse
    from .models import Challenge
    from .rewards import finalize_challenge
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    challenge_id = request.POST.get("challenge_id")
    score = float(request.POST.get("score", 0))
    target = float(request.POST.get("target", 0))
    total = int(request.POST.get("total", 0))
    if not challenge_id:
        return JsonResponse({"error": "challenge_id required"}, status=400)
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Challenge not found"}, status=404)
    if challenge.game_key != 'quiz':
        return JsonResponse({"error": "Not a quiz challenge"}, status=400)
    passed = score >= target
    if target > 0.1:
        denom = target
    else:
        denom = 0.1
    pct = score / denom * 10
    if pct > 10:
        pct = 10
    pct = int(pct)
    challenge.quality_score = pct
    challenge.feedback = f"Quiz: {int(score)}/{int(target)} correct out of {total}"
    challenge.proof_text = f"Quiz: {int(score)}/{total} correct"
    challenge.ai_checked = True
    rw = finalize_challenge(request.user, challenge, passed)
    if total > 1:
        denom = total
    else:
        denom = 1
    accuracy = int(score / denom * 100)
    _save_game_stats_sync(request.user, 'quiz', score, accuracy)
    return JsonResponse({
        'passed': passed,
        'score': challenge.quality_score,
        'feedback': challenge.feedback,
        'xp': challenge.xp_reward,
        'coins': challenge.coin_reward,
        'status': challenge.status,
        'new_level': rw['new_level'],
        'total_xp': rw['total_xp'],
        'total_coins': rw['total_coins'],
    })


# Gives AI feedback on a fitness result (used by the fitness game).
# If removed, the fitness game shows no feedback after a set.
# Change the route in home/urls.py (name='fitness_analyze').
@login_required
def fitness_analyze(request):
    from .ai_service import fitness_feedback
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    exercise = request.POST.get('exercise', 'exercise')
    actual = float(request.POST.get('actual', 0))
    target = float(request.POST.get('target', 0))
    mode = request.POST.get('mode', 'reps')
    elapsed_secs = int(float(request.POST.get('elapsed', 0)))
    feedback = fitness_feedback(exercise, actual, target, mode, elapsed_secs)
    passed = actual >= target
    return JsonResponse({'feedback': feedback, 'passed': passed})


# Rerolls a challenge for the user (free reroll, daily free or 50 coins).
# If removed, the reroll button on challenges page breaks.
# Change the route in home/urls.py (name='challenge_regenerate').
@login_required
def challenge_regenerate(request, challenge_id):
    from django.http import JsonResponse
    from django.utils import timezone
    from .challenge_gen import regenerate_challenge
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=400)
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')
    except Challenge.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Challenge not found or not pending.'}, status=404)
    user = request.user
    today = timezone.now().date()
    cost = 50
    reason = 'coins'
    if user.rerolls > 0:
        user.rerolls -= 1
        cost = 0
        reason = 'free_reroll'
    elif user.last_free_reroll_date != today:
        user.last_free_reroll_date = today
        cost = 0
        reason = 'daily_free'
    else:
        if user.coins < cost:
            return JsonResponse({
                'success': False,
                'message': f'Not enough coins. Reroll costs {cost} coins, or wait for tomorrow\'s free reroll.',
            }, status=400)
        user.coins -= cost
    user.save(update_fields=['coins', 'rerolls', 'last_free_reroll_date'])
    new_ch = regenerate_challenge(challenge, user)
    if new_ch is None:
        if reason == 'coins':
            user.coins += cost
            user.save(update_fields=['coins'])
        elif reason == 'daily_free':
            user.last_free_reroll_date = None
            user.save(update_fields=['last_free_reroll_date'])
        else:
            user.rerolls += 1
            user.save(update_fields=['rerolls'])
        return JsonResponse({'success': False, 'message': 'AI generation failed. Please try again.'}, status=500)
    if reason in ('free_reroll', 'daily_free'):
        message = f'Free reroll used! New challenge: {new_ch.title}'
    else:
        message = f'Rerolled for {cost} coins! New challenge: {new_ch.title}'
    return JsonResponse({
        'success': True,
        'new_id': new_ch.id,
        'total_coins': user.coins,
        'free_rerolls': user.rerolls,
        'cost': cost,
        'reason': reason,
        'message': message,
    })


# Generates extra challenges for the user when they want more.
# If removed, the "generate more" button on challenges page breaks.
# Change the route in home/urls.py (name='challenge_generate_more').
@login_required
def challenge_generate_more(request):
    from django.http import JsonResponse
    from .challenge_gen import generate_more
    try:
        count = int(request.POST.get('count', 0))
        if count < 1:
            count = 0  # 0 = use default (capped at 4)
        if count > 20:
            count = 20  # hard cap
        created = generate_more(request.user, count=count)
        challenges = []
        for c in created:
            challenges.append({'id': c.id, 'title': c.title, 'category': c.category})
        return JsonResponse({
            'success': True,
            'created': len(created),
            'challenges': challenges,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# Deletes a single challenge of the logged in user.
# If removed, the delete button on challenges page breaks.
# Change the route in home/urls.py (name='challenge_delete').
@login_required
def challenge_delete(request, challenge_id):
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=400)
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user)
    except Challenge.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Challenge not found.'}, status=404)
    title = challenge.title
    challenge.delete()
    return JsonResponse({'success': True, 'id': challenge_id, 'title': title})


# Deletes many challenges at once (completed, expired or all).
# If removed, the clear completed buttons on challenges page break.
# Change the route in home/urls.py (name='challenge_delete_bulk').
@login_required
def challenge_delete_bulk(request):
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=400)
    scope = request.POST.get('scope', 'completed')  # completed|expired|all
    qs = Challenge.objects.filter(user=request.user)
    if scope == 'completed':
        qs = qs.filter(status='completed')
    elif scope == 'expired':
        qs = qs.filter(status='expired')
    elif scope == 'all':
        pass
    else:
        return JsonResponse({'success': False, 'message': 'Invalid scope.'}, status=400)
    count = qs.count()
    qs.delete()
    return JsonResponse({'success': True, 'deleted': count, 'scope': scope})


# Streams challenge generation as server sent events to the page.
# If removed, the loading animation for new challenges stalls.
# Change the route in home/urls.py (name='challenge_generate_sse').
@login_required
def challenge_generate_sse(request):
    from django.http import StreamingHttpResponse
    from .challenge_gen import generate_more
    import json, time

    # Generator that yields the sse events to the browser.
    def event_stream():
        try:
            created = generate_more(request.user)
            yield f"data: {json.dumps({'type': 'done', 'created': len(created)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


# Chat with the AI about your challenges, sends the challenge list as context.
# If removed, the challenge AI chat box stops working.
# Change the route in home/urls.py (name='challenge_chat').
@login_required
def challenge_chat(request):
    from django.http import JsonResponse
    import json
    from .models import Challenge, ChatMessage
    from datetime import date
    if request.method == 'GET':
        msgs = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:30]
        history = []
        for m in reversed(msgs):
            history.append({"role": m.role, "content": m.content})
        return JsonResponse({"history": history})
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        file_data = data.get('file_data', '')
        file_type = data.get('file_type', '')
        if not message and not file_data:
            return JsonResponse({"error": "Message or file required"}, status=400)
        pending = list(Challenge.objects.filter(user=request.user, status='pending').order_by('-created_at')[:5])
        if pending:
            ctx = "Current pending challenges:\n"
            for c in pending:
                ctx += f"- [{c.category}] {c.title} ({c.difficulty})\n"
        else:
            recent = list(Challenge.objects.filter(user=request.user).order_by('-created_at')[:5])
            if recent:
                ctx = "Recently completed challenges:\n"
                for c in recent:
                    ctx += f"- [{c.category}] {c.title}\n"
            else:
                ctx = "No challenges yet.\n"
        quiz_ctx = data.get('quiz_context')
        if quiz_ctx and isinstance(quiz_ctx, list) and len(quiz_ctx) > 0:
            ctx += "\n\nCURRENT QUIZ QUESTIONS (DO NOT ANSWER THESE — hints only):\n"
            for i, q in enumerate(quiz_ctx, 1):
                ctx += f"{i}. {q}\n"
        ctx += f"\nUser: L{getattr(request.user, 'level', 1) or 1} · {getattr(request.user, 'xp', 0) or 0} XP · {getattr(request.user, 'coins', 0) or 0} coins"
        from .ai_service import chat_response
        user_content = message
        if file_data and file_type.startswith('image/'):
            if message:
                user_content = f"[Image attached]\n\n{message}"
            else:
                user_content = "[Image attached]"
        elif file_data:
            if message:
                user_content = f"[File attached: {file_type}]\n\n{message}"
            else:
                user_content = "[File attached]"
        prev_msgs = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:30]
        history = []
        for m in reversed(prev_msgs):
            history.append({"role": m.role, "content": m.content})
        ChatMessage.objects.create(user=request.user, role='user', content=user_content)
        custom_keys = {
            "groq": getattr(request.user, 'groq_api_key', '') or None,
            "gemini": getattr(request.user, 'gemini_api_key', '') or None,
            "openrouter": getattr(request.user, 'openrouter_api_key', '') or None,
        }
        models = {
            "groq": 'llama-3.3-70b-versatile',
            "gemini": 'gemini-2.0-flash',
            "openrouter": 'openai/gpt-4o-mini',
        }
        reply = chat_response(
            message, ctx, history=history, custom_keys=custom_keys, models=models,
            ai_name=getattr(request.user, 'ai_name', 'ChillX') or 'ChillX',
            personality=getattr(request.user, 'ai_personality', '') or '',
            image_data=file_data if file_data and file_type.startswith('image/') else None,
        )
        if not reply:
            reply = "Hmm, I couldn't process that. Try asking differently!"
        ChatMessage.objects.create(user=request.user, role='assistant', content=reply)
        return JsonResponse({"reply": reply})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Renders a single in-house mini game page (typing, cps, etc).
# If removed, /games/<name>/ 404s so every mini game breaks.
# Change the route in home/urls.py (name='game') or templates/games/*.html.
@login_required
def game_view(request, game_name):
    from django.shortcuts import render, redirect
    from .models import UserGameStats
    valid_games = {'typing', 'reaction', 'cps', 'memory', 'runner', 'tictactoe', 'aim3d', 'fitness', 'quiz'}
    if game_name not in valid_games:
        return render(request, 'dashboard/home.html', {'user': request.user})
    stats, _ = UserGameStats.objects.get_or_create(user=request.user, game=game_name)
    return render(request, f'games/{game_name}.html', {
        'user': request.user,
        'stats': stats,
    })


# Renders the multiplayer version of a game inside the iframe.
# If removed, /multiplayer-game/<name>/ 404s so the lobby iframe breaks.
# Change the route in home/urls.py (name='multiplayer_game').
@login_required
@xframe_options_sameorigin
def multiplayer_game_view(request, game_name):
    valid_games = {'typing', 'reaction', 'cps', 'memory', 'runner', 'tictactoe', 'aim3d', 'quiz'}
    if game_name not in valid_games:
        from django.shortcuts import redirect
        return redirect('dashboard')
    return render(request, f'games/multiplayer/{game_name}.html', {
        'user': request.user,
    })


# Generates quiz questions for every topic via AI (no hardcoded banks).
# If removed, /quiz/generate-questions/ 404s and the quiz game breaks.
# Change the route in home/urls.py (name='quiz_generate_questions').
@login_required
@csrf_exempt
def quiz_generate_questions(request):
    import random
    topic = request.GET.get('topic', 'mixed')
    count = int(request.GET.get('count', 10))
    if count > 20:
        count = 20
    topics_map = {
        'gk': 'general knowledge (countries, history, science, geography)',
        'tech': 'technology, AI, programming, full forms, computer science',
        'nepali_riddles': 'simple Nepal GK questions written in Nepali Devnagari script (history, geography, culture, festivals) — plain knowledge questions only',
        'riddles': 'fun easy trivia questions with one clear answer — simple word facts and everyday knowledge',
        'nepal': 'Nepal (history, geography, culture, famous figures)',
        'mixed': 'mix of general knowledge, technology, trivia, world facts, and Nepal GK',
    }
    topic_desc = topics_map.get(topic, 'general knowledge')
    is_nepali = topic == 'nepali_riddles'
    prompt = f"""Generate {count} multiple-choice quiz questions about {topic_desc}.
Each question MUST be a JSON object with these exact keys:
- "question": the question text (string)
- "options": an array of exactly 4 answer choices (strings)
- "answer": the correct answer (string, must be one of the 4 options)
- "answer_en": the answer in simple English transliteration for text-input matching (string)
- "explanation": a brief 1-sentence explanation of why the answer is correct (string)
- "language": {"\"ne\" (write question and options in Nepali Devnagari with correct spelling)" if is_nepali else "\"en\""}
Rules:
- Every question must be straightforward with ONE clear meaning — NO double meanings, NO wordplay tricks, NO cheeky or suggestive content
- Make questions decent, fun and educational
- Each question must have exactly 4 unique options
- The correct answer must be exactly one of the 4 options
- The "answer_en" field is key: provide a simple English transliteration so users typing in English letters can match it
- Vary difficulty within the set
- Do NOT number the questions in the text
- Output ONLY a valid JSON array, no markdown, no prose
Example format:
[
  {{"question": "Which planet is closest to the Sun?", "options": ["Mercury", "Venus", "Mars", "Earth"], "answer": "Mercury", "answer_en": "mercury", "explanation": "Mercury orbits closest to the Sun.", "language": "en"}}
]"""
    result = _groq_request([{"role": "user", "content": prompt}], model="llama3-8b-8192", temperature=0.9, max_tokens=4096)
    if not result:
        result = _groq_request([{"role": "user", "content": prompt}], temperature=0.9, max_tokens=4096)
    if not result:
        result = _gemini_request(prompt)
    if not result:
        result = _openrouter_request([{"role": "user", "content": prompt}], temperature=0.9, max_tokens=4096)
    # Parse the JSON result
    questions = None
    if result:
        try:
            # Strip any markdown fences
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            questions = json.loads(cleaned.strip())
            if not isinstance(questions, list):
                raise ValueError("Not a list")
            # Validate structure
            for q in questions:
                for k in ("question", "options", "answer", "explanation"):
                    if k not in q:
                        raise ValueError("Missing keys")
                if len(q["options"]) != 4:
                    raise ValueError("Need exactly 4 options")
                if q["answer"] not in q["options"]:
                    q["answer"] = q["options"][0]  # fix if AI messes up
            random.shuffle(questions)
        except (json.JSONDecodeError, ValueError, KeyError):
            questions = None
    if not questions:
        # No AI key configured or every provider failed — serve the offline
        # bank so the quiz still works (e.g. Render free tier without keys).
        from .quiz_bank import get_local_questions
        questions = get_local_questions(topic, count)
    return JsonResponse({"questions": questions})


# Api endpoint that returns the users stats as json for the dashboard.
# If removed, /api/user-stats/ 404s and the stats bars stop loading.
# Change the route in home/urls.py (name='user_stats_json').
@login_required
def user_stats_json(request):
    from .models import UserGameStats
    user = request.user
    xp = user.xp
    level = user.level
    coins = user.coins
    xp_in_current = xp - (level - 1) * 1000
    xp_next_level = 1000
    if xp_next_level > 0:
        progress = int(xp_in_current / xp_next_level * 100)
    else:
        progress = 0
    if progress > 100:
        progress = 100
    game_stats = UserGameStats.objects.filter(user=user).order_by('-last_played')
    titles = {
        'runner': 'Super Mario Runner', 'typing': 'Typing Rush',
        'reaction': 'Reaction Shot', 'cps': 'CPS Slam',
        'memory': 'Memory Matrix', 'tictactoe': 'Tic Tac Toe',
        'aim3d': 'Aim 3D', 'fitness': 'Fitness', 'quiz': 'Quiz',
    }
    stats_data = []
    for gs in game_stats:
        stats_data.append({
            'game': titles.get(gs.game, gs.game),
            'key': gs.game,
            'best_score': gs.best_score,
            'best_score_secondary': gs.best_score_secondary,
            'plays': gs.plays,
        })
    return JsonResponse({
        'xp': xp,
        'level': level,
        'coins': coins,
        'diamonds': user.diamonds,
        'xp_progress': progress,
        'xp_current': xp_in_current,
        'xp_next': xp_next_level,
        'game_stats': stats_data,
        'display_name': user.display_name or user.username,
        'title': user.title or '',
        'flex_effect': user.flex_effect or '',
        'name_effect': user.name_effect or '',
        'avatar_border': user.avatar_border or '',
        'bg_effect': user.bg_effect or '',
        'has_avatar': bool(user.avatar_base64),
        'avatar_url': '/api/shop/avatar/?user_id=' + str(user.id) if user.avatar_base64 else '',
    })


# Shows the shop page where users buy items with coins.
# If removed, /shop/ 404s and users cant buy anything.
# Change the route in home/urls.py (name='shop') or dashboard/shop.html.
@login_required
def shop_page(request):
    return render(request, 'dashboard/shop.html')


# Shows the inventory page with all owned items.
# If removed, /inventory/ 404s and users cant see their items.
# Change the route in home/urls.py (name='inventory') or dashboard/inventory.html.
@login_required
def inventory_view(request):
    return render(request, 'dashboard/inventory.html')


# Shows achievements and titles page with unlock progress.
# If removed, /achievements/ 404s and users lose achievements page.
# Change the route in home/urls.py (name='achievements') or dashboard/achievement.html.
@login_required
def achievement_page(request):
    from .models import Achievement, UserAchievement, Title, UserTitle
    from .achievement_views import get_level_from_xp, get_tier_for_xp, get_xp_for_level
    user = request.user
    user_level = get_level_from_xp(user.xp)
    user_tier = get_tier_for_xp(user.xp)
    next_xp = get_xp_for_level(user_level + 1)
    xp_to_next = next_xp - user.xp
    if next_xp > 0:
        xp_progress = (user.xp / next_xp) * 100
    else:
        xp_progress = 0
    # Get user achievements
    user_achievements = UserAchievement.objects.filter(user=user)
    achievements = Achievement.objects.all()
    # Update achievement progress in template context
    achievements_data = []
    for achievement in achievements:
        user_achievement = user_achievements.filter(achievement=achievement).first()
        achievements_data.append({
            'id': achievement.id,
            'name': achievement.name,
            'description': achievement.description,
            'category': achievement.category,
            'tier': achievement.tier,
            'icon': achievement.icon,
            'xp_reward': achievement.xp_reward,
            'coin_reward': achievement.coin_reward,
            'max_progress': achievement.max_progress,
            'user_progress': user_achievement.progress if user_achievement else 0,
            'unlocked': user_achievement.unlocked if user_achievement else False,
        })
    # Get titles with user unlock status
    titles_data = []
    all_titles = Title.objects.all()
    user_titles = UserTitle.objects.filter(user=user)
    for title in all_titles:
        ut = user_titles.filter(title=title).first()
        titles_data.append({
            'id': title.id,
            'name': title.name,
            'tier': title.tier,
            'min_xp': title.min_xp,
            'icon': title.icon,
            'unlocked': ut.unlocked if ut else (user.xp >= title.min_xp),
            'equipped': ut.equipped if ut else False,
        })
    # Get equipped title
    user_title = None
    user_title_tier = None
    user_title_obj = UserTitle.objects.filter(user=user, equipped=True).first()
    if user_title_obj:
        user_title = user_title_obj.title
        user_title_tier = user_title_obj.title.tier
    return render(request, 'dashboard/achievement.html', {
        'user': user,
        'user_level': user_level,
        'user_tier': user_tier,
        'user_xp': user.xp,
        'user_xp_to_next': xp_to_next,
        'user_xp_progress': xp_progress,
        'user_title': user.title,
        'user_title_tier': user_title_tier,
        'user_coins': user.coins,
        'user_diamonds': user.diamonds,
        'achievements': achievements_data,
        'titles': titles_data,
        'game_stats': _get_game_stats(user),
    })


# Builds a full game stats list (wins, losses, win rate) for the achievements page.
# If removed, the achievements page shows no game stats.
# Called from achievement_page, no direct url.
def _get_game_stats(user):
    from .models import UserGameStats
    game_titles = {
        'runner': 'Super Mario Runner', 'typing': 'Typing Rush',
        'reaction': 'Reaction Shot', 'cps': 'CPS Slam',
        'memory': 'Memory Matrix', 'tictactoe': 'Tic Tac Toe',
        'aim3d': 'Aim 3D', 'fitness': 'Fitness', 'quiz': 'Quiz',
    }
    stats = UserGameStats.objects.filter(user=user).order_by('-plays')
    result = []
    for gs in stats:
        result.append({
            'game': game_titles.get(gs.game, gs.game),
            'key': gs.game,
            'best_score': gs.best_score,
            'best_score_secondary': gs.best_score_secondary,
            'plays': gs.plays,
            'wins': gs.wins,
            'losses': gs.losses,
            'deaths': gs.deaths,
            'win_rate': gs.win_rate,
        })
    return result


# Api endpoint that saves a games score/win/loss for the logged in user.
# If removed, /api/game/save-stats/ 404s and game stats never update.
# Change the route in home/urls.py (name='save_game_stats').
@login_required
def save_game_stats(request):
    from django.http import JsonResponse
    from django.utils import timezone
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    game = request.POST.get('game', '')
    if not game:
        return JsonResponse({'error': 'game required'}, status=400)
    score = int(request.POST.get('score', 0))
    score_secondary = int(request.POST.get('score_secondary', 0))
    won = request.POST.get('won') == 'true'
    deaths = int(request.POST.get('deaths', 0))
    stats, _ = UserGameStats.objects.get_or_create(user=request.user, game=game)
    stats.plays += 1
    if score > stats.best_score:
        stats.best_score = score
    if score_secondary > stats.best_score_secondary:
        stats.best_score_secondary = score_secondary
    if won:
        stats.wins += 1
    elif request.POST.get('won') == 'false':
        stats.losses += 1
    stats.deaths += deaths
    stats.last_played = timezone.now()
    stats.save()
    return JsonResponse({'ok': True})


# Social feed page - shows all chillx posts with votes and categories.
# If removed, /social/ 404s and the whole social feed breaks.
# Change the route in home/urls.py (name='social') or dashboard/social.html.
@login_required
def social_view(request):
    from .models import SocialPost, Vote, Follow, Story
    from datetime import timedelta
    from django.utils import timezone
    category = request.GET.get('category', '')
    query = SocialPost.objects.all()
    if category:
        query = query.filter(category=category)
    posts = query.select_related('user').prefetch_related('comments__user', 'votes')[:50]
    user_votes = dict(
        Vote.objects.filter(user=request.user, post__in=posts).values_list('post_id', 'value')
    )
    if not request.user.preferences:
        user_categories = CATEGORIES
    else:
        user_categories = []
        for c in CATEGORIES:
            if c['id'] in request.user.preferences:
                user_categories.append(c)
    author_ids = set()
    for p in posts:
        if p.user.id != request.user.id:
            author_ids.add(p.user.id)
    followed_authors = set(Follow.objects.filter(follower=request.user, following_id__in=author_ids).values_list('following_id', flat=True))
    return render(request, 'dashboard/social.html', {
        'posts': posts,
        'categories': user_categories,
        'active_category': category,
        'user_votes': user_votes,
        'user_votes_json': json.dumps(user_votes),
        'followed_authors_json': json.dumps(list(followed_authors)),
    })


# Serves a social post's proof image lazily instead of inlining the base64
# into the feed HTML. The feed was shipping ~8MB of base64 per page load.
# If removed, post images stop loading (they're stored as base64 in the DB).
# Called from <img src="/social/post-image/<id>/"> in social.html.
@login_required
def social_post_image(request, post_id):
    from django.http import HttpResponse
    from .models import SocialPost
    try:
        post = SocialPost.objects.get(id=post_id)
    except SocialPost.DoesNotExist:
        return HttpResponse(status=404)
    data = post.proof_image or ''
    if not data:
        return HttpResponse(status=404)
    # data:image/jpeg;base64,.... — split off the mime prefix if present
    mime = 'image/jpeg'
    if ',' in data and ';base64,' in data:
        head, _, b64 = data.partition(',')
        mime = head.replace('data:', '').replace(';base64', '').strip()
        data = b64
    import base64 as _b64
    try:
        # add back missing padding (browsers tolerate it, Python doesn't)
        data += '=' * (-len(data) % 4)
        raw = _b64.b64decode(data)
    except Exception:
        return HttpResponse(status=400)
    resp = HttpResponse(raw, content_type=mime)
    resp['Cache-Control'] = 'public, max-age=86400'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp


# Handles up/down voting on a social post.
# If removed, the vote buttons on the feed stop working.
# Change the route in home/urls.py (name='social_vote').
@login_required
@csrf_exempt
def social_vote(request, post_id):
    from .models import SocialPost, Vote
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        post = SocialPost.objects.get(id=post_id)
    except SocialPost.DoesNotExist:
        return JsonResponse({'error': 'Post not found'}, status=404)
    try:
        val = int(request.POST.get('value', 0))
    except (ValueError, TypeError):
        val = 0
    if val > 0:
        val = 1
    else:
        val = -1
    vote, created = Vote.objects.get_or_create(post=post, user=request.user, defaults={'value': val})
    if not created:
        if vote.value == val:
            vote.delete()
            post.vote_score -= val
            post.save(update_fields=['vote_score'])
            return JsonResponse({'score': post.vote_score, 'removed': True, 'status': 'unliked'})
        post.vote_score -= vote.value
        vote.value = val
        vote.save(update_fields=['value'])
    post.vote_score += val
    post.save(update_fields=['vote_score'])
    return JsonResponse({'score': post.vote_score, 'status': 'liked'})


# Adds a comment to a social post.
# If removed, the comment box on posts stops working.
# Change the route in home/urls.py (name='social_comment').
@login_required
@csrf_exempt
def social_comment(request, post_id):
    from .models import SocialPost, Comment
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        post = SocialPost.objects.get(id=post_id)
    except SocialPost.DoesNotExist:
        return JsonResponse({'error': 'Post not found'}, status=404)
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'Comment cannot be empty'}, status=400)
    comment = Comment.objects.create(post=post, user=request.user, text=text)
    return JsonResponse({
        'id': comment.id,
        'username': request.user.display_name or request.user.username,
        'has_avatar': bool(request.user.avatar_base64),
        'text': comment.text,
        'created_at': comment.created_at.isoformat(),
    })


# Creates a new social post with text, image or video.
# If removed, /social/create/ 404s so nobody can make posts.
# Change the route in home/urls.py (name='social_create_post').
@login_required
@csrf_exempt
def social_create_post(request):
    from .models import SocialPost
    import base64
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    title = request.POST.get('title', '').strip()
    category = request.POST.get('category', '').strip()
    description = request.POST.get('description', '').strip()
    proof_text = request.POST.get('proof_text', '').strip()
    if not title or not category:
        return JsonResponse({'error': 'Title and category required'}, status=400)
    proof_image = ''
    proof_video = ''
    if request.FILES.get('proof_image'):
        img = request.FILES['proof_image']
        proof_image = 'data:' + img.content_type + ';base64,' + base64.b64encode(img.read()).decode()
    if request.FILES.get('proof_video'):
        vid = request.FILES['proof_video']
        proof_video = 'data:' + vid.content_type + ';base64,' + base64.b64encode(vid.read()).decode()
    post = SocialPost.objects.create(
        user=request.user,
        category=category,
        title=title,
        description=description,
        proof_text=proof_text,
        proof_image=proof_image,
        proof_video=proof_video,
    )
    return JsonResponse({'post_id': post.id, 'redirect': '/social/'})


# Shares a completed challenge as a social post.
# If removed, the share result button after a challenge breaks.
# Change the route in home/urls.py (name='social_share').
@login_required
def social_share(request, challenge_id):
    from .models import Challenge, SocialPost
    try:
        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='completed')
    except Challenge.DoesNotExist:
        return JsonResponse({'error': 'Completed challenge not found'}, status=404)
    existing = SocialPost.objects.filter(challenge=challenge).first()
    if existing:
        return JsonResponse({'error': 'Already shared', 'post_id': existing.id}, status=400)
    post = SocialPost.objects.create(
        challenge=challenge,
        user=request.user,
        category=challenge.category,
        title=f"Completed: {challenge.title}",
        description=challenge.description,
        proof_text=challenge.proof_text,
        proof_image=challenge.proof_image,
    )
    return JsonResponse({'post_id': post.id, 'redirect': '/social/'})


# Deletes the logged in users own social post.
# If removed, the delete button on your posts stops working.
# Change the route in home/urls.py (name='social_delete_post').
@login_required
@csrf_exempt
def social_delete_post(request, post_id):
    from .models import SocialPost
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        post = SocialPost.objects.get(id=post_id, user=request.user)
    except SocialPost.DoesNotExist:
        return JsonResponse({'error': 'Post not found or not yours'}, status=404)
    post.delete()
    return JsonResponse({'success': True})


# Api that returns live vote/comment counts for posts shown on the feed.
# If removed, the feed scores wont refresh in real time.
# Change the route in home/urls.py (name='social_live').
@login_required
def social_live(request):
    from .models import SocialPost, Vote
    post_ids = request.GET.get('ids', '')
    if not post_ids:
        return JsonResponse({'posts': {}})
    ids = []
    for x in post_ids.split(','):
        if x.isdigit():
            ids.append(int(x))
    posts = SocialPost.objects.filter(id__in=ids)
    user_votes = {}
    for v in Vote.objects.filter(post__in=posts, user=request.user):
        user_votes[v.post_id] = v.value
    posts_data = {}
    for p in posts:
        posts_data[p.id] = {
            'score': p.vote_score,
            'comments': p.comments.count(),
            'voted': user_votes.get(p.id, 0),
        }
    return JsonResponse({'posts': posts_data})


# Follows or unfollows another user (toggle).
# If removed, the follow buttons on profiles stop working.
# Change the route in home/urls.py (name='toggle_follow').
@login_required
@csrf_exempt
def toggle_follow(request, user_id):
    from .models import Follow
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if user_id == request.user.id:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
    try:
        target = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        follow.delete()
        return JsonResponse({'following': False})
    return JsonResponse({'following': True})


# Api that searches active users by username for the search box.
# If removed, the user search on social page stops working.
# Change the route in home/urls.py (name='search_users').
@login_required
@csrf_exempt
def search_users_api(request):
    q = request.GET.get('q', '')
    users = User.objects.filter(is_active=True)
    if q:
        users = users.filter(Q(username__icontains=q) | Q(display_name__icontains=q))
    users = users.exclude(id=request.user.id)[:20]
    data = []
    for u in users:
        data.append({
            'id': u.id,
            'username': u.display_name or u.username,
            'has_avatar': bool(u.avatar_base64),
        })
    return JsonResponse({'users': data})


# Sends a friend request to another user.
# If removed, the add friend button stops working.
# Change the route in home/urls.py (name='send_friend_request').
@login_required
@csrf_exempt
def send_friend_request(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if request.user.id == user_id:
        return JsonResponse({'error': 'Cannot send request to yourself'}, status=400)
    try:
        to_user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    existing = FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=to_user) | Q(from_user=to_user, to_user=request.user)
    ).first()
    if existing:
        if existing.status == 'accepted':
            return JsonResponse({'error': 'Already friends'}, status=400)
        if existing.status == 'pending':
            return JsonResponse({'error': 'Request already sent'}, status=400)
        existing.delete()
    FriendRequest.objects.create(from_user=request.user, to_user=to_user)
    return JsonResponse({'ok': True})


# Accepts or rejects a pending friend request.
# If removed, the accept/reject buttons on friend requests break.
# Change the route in home/urls.py (name='respond_friend_request').
@login_required
@csrf_exempt
def respond_friend_request(request, request_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    action = request.POST.get('action', '')
    if action not in ('accept', 'reject'):
        return JsonResponse({'error': 'Invalid action'}, status=400)
    try:
        req = FriendRequest.objects.get(id=request_id, to_user=request.user, status='pending')
    except FriendRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found'}, status=404)
    if action == 'accept':
        req.status = 'accepted'
    else:
        req.status = 'rejected'
    req.save()
    return JsonResponse({'ok': True, 'status': req.status})


# Api that returns the logged in users accepted friends.
# If removed, the friends list on chat/social stops loading.
# Change the route in home/urls.py (name='list_friends').
@login_required
def list_friends_api(request):
    sent = FriendRequest.objects.filter(from_user=request.user, status='accepted').select_related('to_user')
    received = FriendRequest.objects.filter(to_user=request.user, status='accepted').select_related('from_user')
    friends = []
    for req in sent:
        u = req.to_user
        friends.append({'id': u.id, 'username': u.display_name or u.username, 'has_avatar': bool(u.avatar_base64)})
    for req in received:
        u = req.from_user
        friends.append({'id': u.id, 'username': u.display_name or u.username, 'has_avatar': bool(u.avatar_base64)})
    return JsonResponse({'friends': friends})


# Api that returns pending friend requests (received and sent).
# If removed, the pending requests list stops loading.
# Change the route in home/urls.py (name='list_pending').
@login_required
def list_pending_api(request):
    received = FriendRequest.objects.filter(to_user=request.user, status='pending').select_related('from_user')
    sent = FriendRequest.objects.filter(from_user=request.user, status='pending').select_related('to_user')
    data = {'received': [], 'sent': []}
    for req in received:
        u = req.from_user
        data['received'].append({
            'id': req.id, 'user_id': u.id,
            'username': u.display_name or u.username,
            'has_avatar': bool(u.avatar_base64),
            'created_at': req.created_at.isoformat(),
        })
    for req in sent:
        u = req.to_user
        data['sent'].append({
            'id': req.id, 'user_id': u.id,
            'username': u.display_name or u.username,
            'has_avatar': bool(u.avatar_base64),
            'created_at': req.created_at.isoformat(),
        })
    return JsonResponse(data)


# Removes a friend from the logged in users friend list.
# If removed, the unfriend button stops working.
# Change the route in home/urls.py (name='unfriend').
@login_required
@csrf_exempt
def unfriend_api(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    FriendRequest.objects.filter(
        Q(from_user=request.user, to_user_id=user_id, status='accepted') |
        Q(from_user_id=user_id, to_user=request.user, status='accepted')
    ).delete()
    return JsonResponse({'ok': True})


# Returns stories from the user and their friends (last 24 hours).
# If removed, /social/stories/ 404s and the story bar breaks.
# Change the route in home/urls.py (name='get_stories').
@login_required
def get_stories(request):
    from .models import Story, FriendRequest
    from django.db.models import Q
    from datetime import timedelta
    from django.utils import timezone
    Story.objects.filter(created_at__lt=timezone.now()-timedelta(hours=24)).delete()
    cutoff = timezone.now() - timedelta(hours=24)
    # Friends-only: include own stories + friends' stories
    friend_ids = FriendRequest.objects.filter(
        Q(from_user=request.user, status='accepted') |
        Q(to_user=request.user, status='accepted')
    ).values_list('from_user_id', 'to_user_id')
    fids = set()
    for f, t in friend_ids:
        if f == request.user.id:
            fids.add(t)
        else:
            fids.add(f)
    fids.add(request.user.id)
    stories = Story.objects.filter(created_at__gte=cutoff, user_id__in=fids).select_related('user')
    grouped = {}
    now_iso = timezone.now().isoformat()
    for s in stories:
        uid = s.user.id
        if uid not in grouped:
            grouped[uid] = {
                'user_id': uid,
                'username': s.user.display_name or s.user.username,
                'has_avatar': bool(s.user.avatar_base64),
                'stories': [],
            }
        expires_at = s.created_at + timedelta(hours=24)
        grouped[uid]['stories'].append({
            'id': s.id,
            'image': s.image,
            'video': s.video,
            'text': s.text,
            'text_style': s.text_style,
            'time': s.created_at.isoformat(),
            'expires_at': expires_at.isoformat(),
        })
    return JsonResponse({'stories': list(grouped.values()), 'now': now_iso})


# Creates a new story with text, image, video and music.
# If removed, /social/stories/create/ 404s so nobody can post stories.
# Change the route in home/urls.py (name='create_story').
@login_required
@csrf_exempt
def create_story(request):
    from .models import Story
    import base64
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    text = request.POST.get('text', '').strip()
    image = ''
    video = ''
    image_data = request.POST.get('image_data', '')
    if image_data and image_data.startswith('data:'):
        image = image_data
    elif request.FILES.get('image'):
        img = request.FILES['image']
        image = 'data:' + img.content_type + ';base64,' + base64.b64encode(img.read()).decode()
    video_data = request.POST.get('video_data', '')
    if video_data and video_data.startswith('data:'):
        video = video_data
    elif request.FILES.get('video'):
        vid = request.FILES['video']
        video = 'data:' + vid.content_type + ';base64,' + base64.b64encode(vid.read()).decode()
    if not text and not image and not video:
        return JsonResponse({'error': 'Text, image, or video required'}, status=400)
    import json
    text_style_raw = request.POST.get('text_style', '')
    if text_style_raw and text_style_raw != '{}':
        try:
            if text_style_raw.startswith('{'):
                text_style = json.loads(text_style_raw)
            else:
                text_style = {'style': text_style_raw}
        except json.JSONDecodeError:
            text_style = {'style': text_style_raw}
    else:
        text_style = {}
    # Music metadata for separate audio playback in viewer
    music_url = request.POST.get('music_url', '')
    if music_url:
        text_style['music_url'] = music_url
        text_style['music_name'] = request.POST.get('music_name', '')
        text_style['music_artist'] = request.POST.get('music_artist', '')
        text_style['music_thumb'] = request.POST.get('music_thumb', '')
        try:
            text_style['music_start'] = float(request.POST.get('music_start', 0))
            text_style['music_end'] = float(request.POST.get('music_end', 0))
        except ValueError:
            text_style['music_start'] = 0
            text_style['music_end'] = 0
    story = Story.objects.create(user=request.user, image=image, video=video, text=text, text_style=text_style)
    return JsonResponse({'id': story.id})


# Deletes one of the logged in users own stories.
# If removed, the story delete button stops working.
# Change the route in home/urls.py (name='delete_story').
@login_required
@csrf_exempt
def delete_story(request, story_id):
    from .models import Story
    from datetime import timedelta
    from django.utils import timezone
    Story.objects.filter(created_at__lt=timezone.now()-timedelta(hours=24)).delete()
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        story = Story.objects.get(id=story_id, user=request.user)
        story.delete()
        return JsonResponse({'ok': True})
    except Story.DoesNotExist:
        return JsonResponse({'error': 'Story not found or unauthorized'}, status=404)


# Saves a quick emoji reaction on a story.
# If removed, the emoji reactions on stories stop working.
# Change the route in home/urls.py (name='react_to_story').
@login_required
@csrf_exempt
def react_to_story(request, story_id):
    from .models import Story
    from django.db import transaction
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    emoji = request.POST.get('emoji', '').strip()
    if not emoji:
        return JsonResponse({'error': 'Emoji required'}, status=400)
    try:
        story = Story.objects.select_for_update().get(id=story_id)
    except Story.DoesNotExist:
        return JsonResponse({'error': 'Story not found'}, status=404)
    with transaction.atomic():
        if not isinstance(story.text_style, dict):
            story.text_style = {}
        reactions = story.text_style.get('reactions', [])
        if not isinstance(reactions, list):
            reactions = []
        from django.utils import timezone
        reactions.append({
            'user': request.user.id,
            'username': request.user.display_name or request.user.username,
            'emoji': emoji,
            'time': timezone.now().isoformat()
        })
        story.text_style['reactions'] = reactions
        story.save(update_fields=['text_style'])
    return JsonResponse({'ok': True})


# Saves a text reply on a story.
# If removed, the reply box on stories stops working.
# Change the route in home/urls.py (name='reply_to_story').
@login_required
@csrf_exempt
def reply_to_story(request, story_id):
    from .models import Story
    from django.db import transaction
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'Text required'}, status=400)
    try:
        story = Story.objects.select_for_update().get(id=story_id)
    except Story.DoesNotExist:
        return JsonResponse({'error': 'Story not found'}, status=404)
    with transaction.atomic():
        if not isinstance(story.text_style, dict):
            story.text_style = {}
        replies = story.text_style.get('replies', [])
        if not isinstance(replies, list):
            replies = []
        from django.utils import timezone
        reply = {
            'user': request.user.id,
            'username': request.user.display_name or request.user.username,
            'text': text,
            'time': timezone.now().isoformat(),
            'avatar': '/api/shop/avatar/?user_id=' + str(request.user.id) if bool(request.user.avatar_base64) else '',
        }
        replies.append(reply)
        story.text_style['replies'] = replies
        story.save(update_fields=['text_style'])
    return JsonResponse({'ok': True, 'reply': reply})


# Shows the chat page where users message each other.
# If removed, /chatx/ 404s and nobody can open chat.
# Change the route in home/urls.py (name='chatx') or dashboard/chatx.html.
@login_required
def chatx_view(request):
    return render(request, 'dashboard/chatx.html', {
        'user': request.user,
    })


# Sends a chat message (text, image, video or file) to another user.
# If removed, /chatx/send/ 404s so chat sending breaks.
# Change the route in home/urls.py (name='send_message').
@login_required
@csrf_exempt
def send_message(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST
    receiver_id = data.get('receiver_id')
    content = data.get('content', '').strip()
    reply_to_id = data.get('reply_to')
    image = data.get('image', '')
    video = data.get('video', '')
    file_data = data.get('file', '')
    file_name = data.get('file_name', '')
    if not receiver_id or (not content and not image and not video and not file_data):
        return JsonResponse({'error': 'receiver_id and content or file required'}, status=400)
    try:
        receiver = User.objects.get(id=receiver_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    reply_to = None
    if reply_to_id:
        try:
            reply_to = Message.objects.get(id=reply_to_id)
        except Message.DoesNotExist:
            pass
    msg = Message.objects.create(
        sender=request.user, receiver=receiver, content=content,
        reply_to=reply_to, image=image, video=video,
        file=file_data, file_name=file_name
    )
    return JsonResponse({
        'id': msg.id,
        'sender_id': msg.sender.id,
        'sender_name': msg.sender.display_name or msg.sender.username,
        'has_avatar': bool(msg.sender.avatar_base64),
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
        'image': msg.image,
        'video': msg.video,
        'file': msg.file,
        'file_name': msg.file_name,
        'reply_to_id': msg.reply_to_id,
    })


# Returns the message history between the user and another user.
# If removed, /chatx/messages/<id>/ 404s and chat history stops loading.
# Change the route in home/urls.py (name='get_messages').
@login_required
def get_messages(request, user_id):
    msgs = Message.objects.filter(
        sender=request.user, receiver_id=user_id
    ) | Message.objects.filter(
        sender_id=user_id, receiver=request.user
    )
    msgs = msgs.order_by('timestamp').select_related('sender', 'reply_to__sender')
    Message.objects.filter(sender_id=user_id, receiver=request.user, is_read=False).update(is_read=True)

    # Turns a message object into a json dict.
    def serialize_msg(m):
        d = {
            'id': m.id,
            'sender_id': m.sender.id,
            'sender_name': m.sender.display_name or m.sender.username,
            'has_avatar': bool(m.sender.avatar_base64),
            'content': m.content,
            'timestamp': m.timestamp.isoformat(),
            'is_read': m.is_read,
            'image': m.image,
            'video': m.video,
            'file': m.file,
            'file_name': m.file_name,
            'edited': m.edited,
            'deleted': m.deleted,
            'reply_to_id': m.reply_to_id,
        }
        if m.reply_to:
            d['reply_to'] = {
                'id': m.reply_to.id,
                'content': m.reply_to.content,
                'sender_name': m.reply_to.sender.display_name or m.reply_to.sender.username,
                'image': m.reply_to.image,
                'file': m.reply_to.file,
                'file_name': m.reply_to.file_name,
                'deleted': m.reply_to.deleted,
            }
        return d
    messages = []
    for m in msgs:
        messages.append(serialize_msg(m))
    return JsonResponse({'messages': messages})


# Returns a list of all chats the user has with last message and unread.
# If removed, /chatx/conversations/ 404s so the chat list is empty.
# Change the route in home/urls.py (name='get_conversations').
@login_required
def get_conversations(request):
    sent = Message.objects.filter(sender=request.user).values('receiver').distinct()
    received = Message.objects.filter(receiver=request.user).values('sender').distinct()
    user_ids = set()
    for s in sent:
        user_ids.add(s['receiver'])
    for r in received:
        user_ids.add(r['sender'])
    users = User.objects.filter(id__in=user_ids)
    # Last message with each peer — one query (newest first) instead of
    # one query per conversation.
    latest = {}
    last_msgs = (
        Message.objects.filter(sender=request.user, receiver_id__in=user_ids)
        | Message.objects.filter(sender_id__in=user_ids, receiver=request.user)
    ).order_by('-timestamp')
    for m in last_msgs:
        peer = m.receiver_id if m.sender_id == request.user.id else m.sender_id
        if peer not in latest:
            latest[peer] = m
        if len(latest) >= len(user_ids):
            break
    # Unread count per peer — one grouped query.
    unread_counts = {
        r['sender_id']: r['count']
        for r in Message.objects.filter(receiver=request.user, is_read=False)
        .values('sender_id')
        .annotate(count=Count('id'))
    }
    conversations = []
    for u in users:
        lm = latest.get(u.id)
        conversations.append({
            'user_id': u.id,
            'username': u.display_name or u.username,
            'has_avatar': bool(u.avatar_base64),
            'last_message': lm.content if lm else '',
            'last_time': lm.timestamp.isoformat() if lm else '',
            'unread': unread_counts.get(u.id, 0),
        })

    # Sort key so conversations sort by latest message time.
    def conversation_time(c):
        return c['last_time']
    conversations.sort(key=conversation_time, reverse=True)
    return JsonResponse({'conversations': conversations})


# Edits one of the logged in users own chat messages.
# If removed, /chatx/edit/ 404s so editing messages breaks.
# Change the route in home/urls.py (name='edit_message').
@login_required
@csrf_exempt
def edit_message(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST
    msg_id = data.get('message_id')
    content = data.get('content', '').strip()
    if not msg_id or not content:
        return JsonResponse({'error': 'message_id and content required'}, status=400)
    try:
        msg = Message.objects.get(id=msg_id, sender=request.user)
    except Message.DoesNotExist:
        return JsonResponse({'error': 'Message not found or not yours'}, status=404)
    msg.content = content
    msg.edited = True
    msg.save(update_fields=['content', 'edited'])
    return JsonResponse({'success': True, 'content': msg.content})


# Soft deletes one of the logged in users own chat messages.
# If removed, /chatx/delete/ 404s so deleting messages breaks.
# Change the route in home/urls.py (name='delete_message').
@login_required
@csrf_exempt
def delete_message(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST
    msg_id = data.get('message_id')
    if not msg_id:
        return JsonResponse({'error': 'message_id required'}, status=400)
    try:
        msg = Message.objects.get(id=msg_id, sender=request.user)
    except Message.DoesNotExist:
        return JsonResponse({'error': 'Message not found or not yours'}, status=404)
    msg.deleted = True
    msg.content = ''
    msg.image = ''
    msg.video = ''
    msg.file = ''
    msg.file_name = ''
    msg.save(update_fields=['deleted', 'content', 'image', 'video', 'file', 'file_name'])
    return JsonResponse({'success': True})


# Api that lists users to chat with, filtered by a search query.
# If removed, /chatx/users/ 404s so the chat sidebar user list breaks.
# Change the route in home/urls.py (name='chat_users').
@login_required
def chat_users(request):
    q = request.GET.get('q', '')
    users = User.objects.exclude(id=request.user.id)
    if q:
        users = users.filter(username__icontains=q) | users.filter(display_name__icontains=q)
    users = users[:20]
    users_data = []
    for u in users:
        users_data.append({
            'id': u.id,
            'username': u.display_name or u.username,
            'has_avatar': bool(u.avatar_base64),
        })
    return JsonResponse({'users': users_data})


# Stores a webrtc call signal (offer/answer/ice/end) for another user.
# If removed, voice/video calls stop connecting.
# Change the route in home/urls.py (name='send_call_signal').
@login_required
@csrf_exempt
def send_call_signal(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from .models import CallSignal
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST
    signal_type = data.get('type', '')
    signal_data = data.get('data', '')
    if signal_type not in ('offer', 'answer', 'ice', 'end', 'cam'):
        return JsonResponse({'error': 'Invalid signal type'}, status=400)
    try:
        callee = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    import logging
    logger = logging.getLogger(__name__)
    if isinstance(signal_data, dict):
        data_str = json.dumps(signal_data)
    elif isinstance(signal_data, str):
        data_str = signal_data
    else:
        data_str = json.dumps(signal_data)
    logger.info('CallSignal: %s -> %s type=%s len(data)=%d', request.user.id, callee.id, signal_type, len(data_str))
    CallSignal.objects.create(
        caller=request.user, callee=callee,
        signal_type=signal_type, data=data_str
    )
    return JsonResponse({'ok': True})


# Returns pending call signals for the user and deletes them.
# If removed, /chatx/call/poll/ 404s so calls never connect.
# Change the route in home/urls.py (name='poll_call_signals').
@login_required
def poll_call_signals(request):
    from .models import CallSignal
    signals = CallSignal.objects.filter(callee=request.user)[:50]
    data = []
    ids = []
    for s in signals:
        ids.append(s.id)
        data.append({
            'id': s.id,
            'caller_id': s.caller.id,
            'caller_name': s.caller.display_name or s.caller.username,
            'caller_avatar': bool(s.caller.avatar_base64),
            'type': s.signal_type,
            'data': s.data,
            'created_at': s.created_at.isoformat(),
        })
    if ids:
        CallSignal.objects.filter(id__in=ids).delete()
    return JsonResponse({'signals': data})


# Checks if a call offer is active with the given user (last 30 sec).
# If removed, /chatx/call/status/<id>/ 404s so call status breaks.
# Change the route in home/urls.py (name='call_status').
@login_required
def call_status(request, user_id):
    from .models import CallSignal
    recent = CallSignal.objects.filter(
        caller=request.user, callee_id=user_id, signal_type='offer',
        created_at__gte=timezone.now() - timedelta(seconds=30)
    ).exists()
    return JsonResponse({'has_offer': recent})


# Profile page for a specific user showing their posts and stories.
# If removed, /social/profile/<id>/ 404s so profiles stop opening.
# Change the route in home/urls.py (name='social_profile').
@login_required
def social_profile_view(request, user_id):
    from .models import SocialPost, Story, FriendRequest
    from django.db.models import Q
    from datetime import timedelta
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    UserModel = get_user_model()
    try:
        profile_user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        raise Http404
    # Profile user's posts
    posts = SocialPost.objects.filter(user=profile_user).select_related('user')[:20]
    # Profile user's active stories
    cutoff = timezone.now() - timedelta(hours=24)
    stories = Story.objects.filter(user=profile_user, created_at__gte=cutoff)[:10]
    # Check friendship
    is_friend = FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=profile_user, status='accepted') |
        Q(to_user=request.user, from_user=profile_user, status='accepted')
    ).exists()
    # Map interests from preferences
    cat_map = {}
    for c in CATEGORIES:
        cat_map[c['id']] = c['name']
    interests = []
    for p in (profile_user.preferences or []):
        interests.append(cat_map.get(p, p))
    return render(request, 'dashboard/social_profile.html', {
        'profile_user': profile_user,
        'posts': posts,
        'stories': stories,
        'is_friend': is_friend,
        'interests': interests,
        'is_own': request.user.id == profile_user.id,
    })


# Redirects a username url to the profile page (lookup by username/display).
# If removed, /social/profile/by-username/<name>/ 404s so profile links break.
# Change the route in home/urls.py (name='social_profile_by_username').
def social_profile_by_username(request, username):
    from django.contrib.auth import get_user_model
    from django.shortcuts import redirect
    from django.http import Http404
    UserModel = get_user_model()
    try:
        user = UserModel.objects.get(username__iexact=username)
    except UserModel.DoesNotExist:
        try:
            user = UserModel.objects.get(display_name__iexact=username)
        except UserModel.DoesNotExist:
            raise Http404
    return redirect('social_profile', user_id=user.id)


# Renders the multiplayer lobby page.
# If removed, /multiplayer/ 404s so the whole multiplayer feature breaks.
# Change the route in home/urls.py (name='multiplayer') or multiplayer.html.
@login_required
# TEMPORARY debug endpoint — dump room cache state. Remove before shipping.
@login_required
def debug_room_dump(request, room_code):
    from django.core.cache import cache
    import json as _json
    room = cache.get(f'room_{room_code}')
    if not room:
        return JsonResponse({'error': 'room not in cache'}, status=404)
    safe = {}
    for k, v in room.items():
        if k == 'quiz_answers':
            safe[k] = {kk: {kkk: (str(vvv)[:40] if not isinstance(vvv, bool) else vvv) for kkk, vvv in vv.items()} for kk, vv in v.items()} if isinstance(v, dict) else v
        elif k == 'players':
            safe[k] = [{kk: vv for kk, vv in p.items() if kk in ('user_id', 'username', 'is_ready', 'connected', 'channel_name')} for p in v]
        else:
            safe[k] = v
    return JsonResponse(safe)


def multiplayer_view(request):
    import json
    user_json = json.dumps({
        'id': request.user.id,
        'username': request.user.username,
        'display_name': request.user.display_name or request.user.username,
        'level': request.user.level,
    })
    return render(request, 'multiplayer.html', {'user_json': user_json})


# Creates a new multiplayer room in cache with the creator as player 0.
# If removed, /multiplayer/create/ 404s so nobody can make a room.
# Change the route in home/urls.py (name='multiplayer_create').
@login_required
def multiplayer_create_room(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}
    challenge_type = data.get('challenge_type', 'typing')
    room_code = generate_room_code()
    avatar_url = f"/api/shop/avatar/?user_id={request.user.id}"
    room = {
        'room_code': room_code,
        'players': [
            {
                'user_id': request.user.id,
                'username': request.user.username,
                'display_name': request.user.display_name or request.user.username,
                'avatar': avatar_url,
                'level': request.user.level,
                'rank': get_rank(request.user.level),
                'is_ready': False,
                'channel_name': '',
                'connected': False,
            }
        ],
        'challenge_type': challenge_type,
        'challenge': None,
        'status': 'waiting',
        'winner_id': None,
        'winner_username': '',
        'started_at': None,
        'disconnected_player_id': None,
        'disconnect_time': None,
    }
    cache.set(f'room_{room_code}', room, timeout=3600)
    players_data = []
    for p in room['players']:
        players_data.append({
            'user_id': p['user_id'],
            'username': p['username'],
            'display_name': p.get('display_name', p['username']),
            'avatar': p.get('avatar', ''),
            'level': p.get('level', 1),
            'rank': p.get('rank', 'Beginner'),
            'is_ready': p.get('is_ready', False),
            'connected': p.get('connected', False),
        })
    return JsonResponse({
        'room_code': room_code,
        'room': {
            'room_code': room_code,
            'players': players_data,
            'status': room['status'],
            'challenge_type': room['challenge_type'],
        }
    })


# Adds the user to an existing room by code (or returns state if already in).
# If removed, /multiplayer/join/ 404s so nobody can join rooms.
# Change the route in home/urls.py (name='multiplayer_join').
@login_required
def multiplayer_join_room(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    room_code = data.get('room_code', '').upper().strip()
    if not room_code:
        return JsonResponse({'error': 'Room code required'}, status=400)
    room = cache.get(f'room_{room_code}')
    if not room:
        return JsonResponse({'error': 'Room not found or expired'}, status=404)
    if room['status'] == 'active':
        return JsonResponse({'error': 'Game already in progress'}, status=400)
    if len(room['players']) >= 8:
        return JsonResponse({'error': 'Room is full'}, status=400)
    already_in_room = False
    for p in room['players']:
        if p['user_id'] == request.user.id:
            already_in_room = True
            break
    if already_in_room:
        # Reset finished rooms for replay (HTTP fallback for page reloads)
        if room['status'] == 'finished':
            room['status'] = 'waiting'
            room['challenge_type'] = room.get('challenge_type', 'typing')
            room['custom_settings'] = room.get('custom_settings')
            room.pop('challenge', None)
            for p in room['players']:
                p['is_ready'] = False
            cache.set(f'room_{room_code}', room)
        players_data = []
        for p in room['players']:
            players_data.append({
                'user_id': p['user_id'],
                'username': p['username'],
                'display_name': p.get('display_name', p['username']),
                'avatar': p.get('avatar', ''),
                'level': p.get('level', 1),
                'rank': p.get('rank', 'Beginner'),
                'is_ready': p.get('is_ready', False),
                'connected': p.get('connected', False),
            })
        return JsonResponse({
            'room_code': room_code,
            'room': {
                'room_code': room_code,
                'players': players_data,
                'status': room['status'],
                'challenge_type': room['challenge_type'],
                'custom_settings': room.get('custom_settings'),
            }
        })
    avatar_url = f"/api/shop/avatar/?user_id={request.user.id}"
    room['players'].append({
        'user_id': request.user.id,
        'username': request.user.username,
        'display_name': request.user.display_name or request.user.username,
        'avatar': avatar_url,
        'level': request.user.level,
        'rank': get_rank(request.user.level),
        'is_ready': False,
        'channel_name': '',
        'connected': False,
    })
    cache.set(f'room_{room_code}', room, timeout=3600)
    players_data = []
    for p in room['players']:
        players_data.append({
            'user_id': p['user_id'],
            'username': p['username'],
            'display_name': p.get('display_name', p['username']),
            'avatar': p.get('avatar', ''),
            'level': p.get('level', 1),
            'rank': p.get('rank', 'Beginner'),
            'is_ready': p.get('is_ready', False),
            'connected': p.get('connected', False),
        })
    return JsonResponse({
        'room_code': room_code,
        'room': {
            'room_code': room_code,
            'players': players_data,
            'status': room['status'],
            'challenge_type': room['challenge_type'],
            'custom_settings': room.get('custom_settings'),
        }
    })


# Saves a chat message into the room cache list.
# If removed, /multiplayer/chat/send/ 404s so lobby chat sending breaks.
# Change the route in home/urls.py (name='multiplayer_chat_send').
@login_required
def multiplayer_chat_send(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    room_code = data.get('room_code', '').upper().strip()
    text = data.get('message', '').strip()
    if not room_code or not text:
        return JsonResponse({'error': 'room_code and message required'}, status=400)
    room = cache.get(f'room_{room_code}')
    if not room:
        return JsonResponse({'error': 'Room not found'}, status=404)
    is_member = False
    for p in room['players']:
        if p['user_id'] == request.user.id:
            is_member = True
            break
    if not is_member:
        return JsonResponse({'error': 'Not in this room'}, status=403)
    key = f'chat_msgs_{room_code}'
    seq_key = f'chat_seq_{room_code}'
    msgs = cache.get(key) or []
    msg_id = (cache.get(seq_key) or 0) + 1
    cache.set(seq_key, msg_id, timeout=300)
    msgs.append({
        'id': msg_id,
        'sender_id': request.user.id,
        'sender_name': request.user.display_name or request.user.username,
        'text': text,
        'timestamp': time.time(),
    })
    cache.set(key, msgs, timeout=300)
    return JsonResponse({'ok': True, 'message_id': msg_id})


# Returns new lobby chat messages after the given id.
# If removed, /multiplayer/chat/poll/ 404s so lobby chat breaks.
# Change the route in home/urls.py (name='multiplayer_chat_poll').
@login_required
def multiplayer_chat_poll(request):
    room_code = request.GET.get('room_code', '').upper().strip()
    after = int(request.GET.get('after', 0))
    if not room_code:
        return JsonResponse({'error': 'room_code required'}, status=400)
    key = f'chat_msgs_{room_code}'
    msgs = cache.get(key) or []
    new_msgs = []
    for m in msgs:
        if m['id'] > after:
            new_msgs.append(m)
    return JsonResponse({'messages': new_msgs})


# Returns the current room state (players, status, winner) as json.
# If removed, /multiplayer/room/<code>/ 404s so room status checks break.
# Change the route in home/urls.py (name='multiplayer_room_state').
@login_required
def multiplayer_room_state(request, room_code):
    room_code = room_code.upper().strip()
    room = cache.get(f'room_{room_code}')
    if not room:
        return JsonResponse({'error': 'Room not found'}, status=404)
    players_data = []
    for p in room['players']:
        players_data.append({
            'user_id': p['user_id'],
            'username': p['username'],
            'display_name': p.get('display_name', p['username']),
            'avatar': p.get('avatar', ''),
            'level': p.get('level', 1),
            'rank': p.get('rank', 'Beginner'),
            'is_ready': p.get('is_ready', False),
            'connected': p.get('connected', False),
        })
    return JsonResponse({
        'room_code': room_code,
        'players': players_data,
        'status': room['status'],
        'challenge_type': room['challenge_type'],
        'winner_id': room.get('winner_id'),
        'winner_username': room.get('winner_username', ''),
    })

