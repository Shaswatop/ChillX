import json
import random
import string
from datetime import date, timedelta

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.db.models import Q
from django.core.cache import cache

from .models import Challenge, Message, FriendRequest
from .consumers import generate_room_code, get_rank
from .achievement_views import get_level_from_xp, get_tier_for_xp, get_xp_for_level

from .ai_service import chat_response, _groq_request, _gemini_request, _openrouter_request



User = get_user_model()





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





def logout_view(request):

    logout(request)

    return redirect('signin')





def chillx_view(request):

    """Legacy /chillx/ route — redirect to the dashboard."""

    from django.shortcuts import redirect

    return redirect('dashboard')





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





@login_required

def onboarding_view(request):

    if request.user.preferences:

        return redirect('create_profile' if not request.user.display_name else 'dashboard')

    if request.method == 'POST':

        cats = request.POST.getlist('categories')

        request.user.preferences = cats

        request.user.save(update_fields=['preferences'])

        return redirect('create_profile')

    return render(request, 'onboarding.html', {'categories': CATEGORIES})





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



@login_required

def dashboard_view(request):

    from .models import UserGameStats

    user = request.user
    xp = user.xp
    level = user.level
    coins = user.coins
    xp_in_current = xp - (level - 1) * 1000
    xp_next_level = 1000
    progress = min(int(xp_in_current / max(xp_next_level, 1) * 100), 100)

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



THEMES = [

    {'id': 'dark-purple', 'name': 'Dark Purple', 'color': 'linear-gradient(135deg,#2d1b4e,#1a0a2e)'},

    {'id': 'crimson', 'name': 'Crimson', 'color': 'linear-gradient(135deg,#4e1b1b,#2e0a0a)'},

    {'id': 'emerald', 'name': 'Emerald', 'color': 'linear-gradient(135deg,#1b4e2d,#0a2e1a)'},

    {'id': 'sapphire', 'name': 'Sapphire', 'color': 'linear-gradient(135deg,#1b2d4e,#0a1a2e)'},

    {'id': 'golden', 'name': 'Golden', 'color': 'linear-gradient(135deg,#4e3e1b,#2e240a)'},

    {'id': 'void', 'name': 'Void', 'color': 'linear-gradient(135deg,#0a0a0a,#1a1a2e)'},

]



FRAMES = [

    {'id': 'none', 'name': 'None'},

    {'id': 'golden_crown', 'name': 'Golden Crown'},

    {'id': 'crystal_spikes', 'name': 'Crystal Spikes'},

    {'id': 'shadow_flame', 'name': 'Shadow Flame'},

    {'id': 'runic_circle', 'name': 'Runic Circle'},

    {'id': 'frost_ring', 'name': 'Frost Ring'},

    {'id': 'void_echo', 'name': 'Void Echo'},

]



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





SETTINGS_CONTEXT = {

    'categories': CATEGORIES,

    'titles': TITLES,

    'themes': THEMES,

    'frames': FRAMES,

    'groq_models': GROQ_MODELS,

    'gemini_models': GEMINI_MODELS,

}


def _player_context(user):
    from .models import UserGameStats
    xp = user.xp
    level = user.level
    coins = user.coins
    xp_in_current = xp - (level - 1) * 1000
    xp_next_level = 1000
    progress = min(int(xp_in_current / max(xp_next_level, 1) * 100), 100)

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



def home_view(request):

    if request.user.is_authenticated:

        return redirect('dashboard')

    return redirect('signin')





@login_required

def challenges_view(request):

    from .challenge_gen import get_todays_challenges, auto_generate_daily

    from .user_performance import get_streak

    today = date.today()

    user = request.user



    # Auto-generate today's challenges on first visit of the day.

    # This is the "trained" part — every daily visit becomes a fresh batch.

    try:

        auto_generate_daily(user)

    except Exception:

        # Never let generation failure block the page render

        pass



    challenges = get_todays_challenges(user)

    completed_today = user.challenges.filter(created_at=today, status='completed').count()

    pending_count = sum(1 for c in challenges if c.status == 'pending')

    submitted_count = sum(1 for c in challenges if c.status == 'submitted')

    streak = get_streak(user)



    return render(request, 'challenges.html', {

        'challenges': challenges,

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





@login_required

def challenge_submit(request, challenge_id):

    from .ai_service import check_submission_text, check_submission_image

    try:

        challenge = Challenge.objects.get(id=challenge_id, user=request.user, status='pending')

    except Challenge.DoesNotExist:

        return redirect('challenges')



    if request.method == 'POST':

        proof_text = request.POST.get('proof_text', '').strip()

        proof_image = request.POST.get('proof_image', '').strip()



        # AI Check: try image first, fall back to text description if image AI fails

        if challenge.proof_type == 'image' and proof_image:

            result = check_submission_image(challenge.title, challenge.description, proof_image)

            # If image AI returned the hard fallback (score=1, AI unavailable),

            # try text check as backup using the user's description

            if not result.get('passed') and result.get('score', 0) <= 2 and 'unavailable' in result.get('feedback', '') and proof_text:

                result = check_submission_text(challenge.title, challenge.description, proof_text)

                # If text also failed, still mark as submitted (manual review)

        else:

            result = check_submission_text(challenge.title, challenge.description, proof_text)



        score = result.get('score', 7)

        feedback = result.get('feedback', 'Well done!')

        passed = result.get('passed', score >= 5)



        challenge.proof_text = proof_text

        challenge.proof_image = proof_image

        challenge.quality_score = score

        challenge.feedback = feedback

        challenge.ai_checked = True



        if passed:

            challenge.status = 'completed'

            from django.utils import timezone

            challenge.completed_at = timezone.now()

            # Award XP and coins (with boost multiplier)

            xp_mult = 1 + (request.user.xp_boosts * 0.5)

            user = request.user

            user.xp += int(challenge.xp_reward * xp_mult)

            user.coins += challenge.coin_reward

            # Level up check (every 1000 XP)

            new_level = user.xp // 1000 + 1

            if new_level > user.level:

                user.coins += 50  # Level up bonus

                user.level = new_level

            user.save(update_fields=['xp', 'coins', 'level'])

        else:

            challenge.status = 'submitted'

            new_level = request.user.level



        challenge.save()



        from django.http import JsonResponse
    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })


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


@login_required

def verify_cps(request):

    from django.http import JsonResponse

    from .models import Challenge

    from django.utils import timezone

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

    challenge.quality_score = int(min(score / target * 10, 10))

    challenge.feedback = f"CPS: {score}/{target} ({clicks} clicks in {seconds}s)"

    challenge.proof_text = f"CPS: {score} in {seconds}s"

    challenge.ai_checked = True

    if passed:

        challenge.status = 'completed'

        challenge.completed_at = timezone.now()

        xp_mult = 1 + (request.user.xp_boosts * 0.5)

        user = request.user

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

    _save_game_stats_sync(request.user, 'cps', score, clicks)

    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })



@login_required

def verify_reaction(request):

    from django.http import JsonResponse

    from .models import Challenge

    from django.utils import timezone

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

    challenge.quality_score = int(max(10 - (avg / max(target, 1)) * 10, 0))

    challenge.feedback = f"Reaction: {avg}/{target}ms avg, best {best}ms ({attempts} attempts)"

    challenge.proof_text = f"Reaction: {avg}ms avg in {attempts} attempts"

    challenge.ai_checked = True

    if passed:

        challenge.status = 'completed'

        challenge.completed_at = timezone.now()

        xp_mult = 1 + (request.user.xp_boosts * 0.5)

        user = request.user

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

    _save_game_stats_sync(request.user, 'reaction', best, attempts)

    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })



@login_required

def verify_typing(request):

    from django.http import JsonResponse

    from .models import Challenge

    from django.utils import timezone

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

    challenge.quality_score = int(min(score / max(target, 1) * 10, 10))

    challenge.feedback = f"Typing: {score}/{target} WPM ({accuracy}% accuracy)"

    challenge.proof_text = f"Typing: {score} WPM, {words} words, {accuracy}% accuracy"

    challenge.ai_checked = True

    if passed:

        challenge.status = 'completed'

        challenge.completed_at = timezone.now()

        xp_mult = 1 + (request.user.xp_boosts * 0.5)

        user = request.user

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

    _save_game_stats_sync(request.user, 'typing', score, accuracy)

    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })




@login_required

def verify_memory(request):

    from django.http import JsonResponse

    from .models import Challenge

    from django.utils import timezone

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

    challenge.quality_score = int(min(score / max(target, 1) * 10, 10))

    challenge.feedback = f"Memory: level {score}/{target}"

    challenge.proof_text = f"Memory: level {score}"

    challenge.ai_checked = True

    if passed:

        challenge.status = 'completed'

        challenge.completed_at = timezone.now()

        xp_mult = 1 + (request.user.xp_boosts * 0.5)

        user = request.user

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

    _save_game_stats_sync(request.user, 'memory', score)

    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })



@login_required

def verify_runner(request):

    from django.http import JsonResponse

    from .models import Challenge

    from django.utils import timezone

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

    challenge.quality_score = int(min(score / max(target, 1) * 10, 10))

    challenge.feedback = f"Runner: {score}/{target} points"

    challenge.proof_text = f"Runner: {score} points"

    challenge.ai_checked = True

    if passed:

        challenge.status = 'completed'

        challenge.completed_at = timezone.now()

        xp_mult = 1 + (request.user.xp_boosts * 0.5)

        user = request.user

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

    _save_game_stats_sync(request.user, 'runner', score)

    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })



@login_required

def verify_tictactoe(request):

    from django.http import JsonResponse

    from .models import Challenge

    from django.utils import timezone

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

    challenge.quality_score = 10 if won else 0

    challenge.feedback = f"TicTacToe: {'Won' if won else 'Lost'} (session: {wins}W/{losses}L)"

    challenge.proof_text = f"TicTacToe: {'Won' if won else 'Lost'}"

    challenge.ai_checked = True

    if passed:

        challenge.status = 'completed'

        challenge.completed_at = timezone.now()

        xp_mult = 1 + (request.user.xp_boosts * 0.5)

        user = request.user

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

    _save_game_stats_sync(request.user, 'tictactoe', wins)

    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })



@login_required

def verify_aim3d(request):

    from django.http import JsonResponse

    from .models import Challenge

    from django.utils import timezone

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

    challenge.quality_score = int(min(score / target * 10, 10)) if target else 5

    challenge.feedback = f"Aim3D: {score}/{target} pts ({accuracy}, {hits} hits)"

    challenge.proof_text = f"Aim3D: {score} pts"

    challenge.ai_checked = True

    if passed:

        challenge.status = 'completed'

        challenge.completed_at = timezone.now()

        xp_mult = 1 + (request.user.xp_boosts * 0.5)

        user = request.user

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

    _save_game_stats_sync(request.user, 'aim3d', score, hits)

    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })



@login_required

def verify_fitness(request):

    from django.http import JsonResponse

    from .models import Challenge

    from django.utils import timezone

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

    pct = int(min(actual / max(target, 0.1) * 10, 10))

    challenge.quality_score = pct

    mode_label = {"reps": "reps", "time": "sec", "distance": "km"}.get(mode, "")

    challenge.feedback = f"Fitness: {exercise} {int(actual)}{mode_label}/{int(target)}{mode_label}"

    challenge.proof_text = f"Fitness: {exercise} {int(actual)}{mode_label}"

    challenge.ai_checked = True

    if passed:

        challenge.status = 'completed'

        challenge.completed_at = timezone.now()

        xp_mult = 1 + (request.user.xp_boosts * 0.5)

        user = request.user

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

    _save_game_stats_sync(request.user, 'fitness', actual)

    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })


@login_required
def verify_quiz(request):

    from django.http import JsonResponse

    from .models import Challenge

    from django.utils import timezone

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

    pct = int(min(score / max(target, 0.1) * 10, 10))

    challenge.quality_score = pct

    challenge.feedback = f"Quiz: {int(score)}/{int(target)} correct out of {total}"

    challenge.proof_text = f"Quiz: {int(score)}/{total} correct"

    challenge.ai_checked = True

    if passed:

        challenge.status = 'completed'

        challenge.completed_at = timezone.now()

        xp_mult = 1 + (request.user.xp_boosts * 0.5)

        user = request.user

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

    _save_game_stats_sync(request.user, 'quiz', score, int(score / max(total, 1) * 100))

    return JsonResponse({

        'passed': passed,

        'score': challenge.quality_score,

        'feedback': challenge.feedback,

        'xp': challenge.xp_reward,

        'coins': challenge.coin_reward,

        'status': challenge.status,

    })


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

    return JsonResponse({

        'success': True,

        'new_id': new_ch.id,

        'total_coins': user.coins,

        'free_rerolls': user.rerolls,

        'cost': cost,

        'reason': reason,

        'message': (f'Free reroll used! New challenge: {new_ch.title}' if reason in ('free_reroll', 'daily_free')

                    else f'Rerolled for {cost} coins! New challenge: {new_ch.title}'),

    })



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

        return JsonResponse({

            'success': True,

            'created': len(created),

            'challenges': [{'id': c.id, 'title': c.title, 'category': c.category} for c in created],

        })

    except Exception as e:

        return JsonResponse({'success': False, 'message': str(e)}, status=500)





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



@login_required

def challenge_generate_sse(request):

    from django.http import StreamingHttpResponse

    from .challenge_gen import generate_more

    import json, time

    def event_stream():

        try:

            created = generate_more(request.user)

            yield f"data: {json.dumps({'type': 'done', 'created': len(created)})}\n\n"

        except Exception as e:

            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')



@login_required

def challenge_chat(request):

    from django.http import JsonResponse

    import json

    from .models import Challenge, ChatMessage

    from datetime import date

    if request.method == 'GET':

        msgs = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:30]

        history = [{"role": m.role, "content": m.content} for m in reversed(msgs)]

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

            user_content = f"[Image attached]\n\n{message}" if message else "[Image attached]"

        elif file_data:

            user_content = f"[File attached: {file_type}]\n\n{message}" if message else "[File attached]"

        prev_msgs = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:30]
        history = [{"role": m.role, "content": m.content} for m in reversed(prev_msgs)]

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

@login_required
@csrf_exempt
def quiz_generate_questions(request):

    """Generate quiz questions via AI for the quiz game."""
    import random
    topic = request.GET.get('topic', 'mixed')

    count = min(int(request.GET.get('count', 10)), 20)



    topics_map = {

        'gk': 'general knowledge (countries, history, science, geography)',

        'tech': 'technology, AI, programming, full forms, computer science',

        'nepali_riddles': 'Nepali Gau Khane Katha riddles in Devnagari script (Nepali language) with double meanings, witty wordplay, and funny twists — like TikTok viral Nepali riddles',

        'riddles': 'funny riddles with double meanings and witty wordplay in the style of Nepali Gau Khane Katha — creative, fresh, never obvious',

        'nepal': 'Nepal (history, geography, culture, famous figures)',

        'mixed': 'mix of general knowledge, technology, riddles, world trivia, and Nepal GK',

    }

    topic_desc = topics_map.get(topic, 'general knowledge')

    is_nepali = topic == 'nepali_riddles'

    # Hardcoded Nepali Gau Khane Katha riddles
    GAU_KHANE_KATHA = [
        {"question":"अंजुलीभरि सुनका मुन्द्रा । के हो ?","options":["नाकको फुली","दुनो","बादल","चुङगम"],"answer":"दुनो","answer_en":"दुनो","explanation":"दुनोमा साना गोलाकार दाना हुन्छन्, जसलाई सुनका मुन्द्रा जस्तै तुलना गरिएको हो।","language":"ne"},
        {"question":"अजङ्गे बाबु, बझाङ्गे छोरो, कालो नाति सेतो पनाति । के हो ?","options":["आगो","दाँत","छाता","कटुसको फल"],"answer":"कटुसको फल","answer_en":"कटुसको फल","explanation":"बोट, फल र भित्री भागको फरक–फरक रंगलाई परिवारसँग तुलना गरिएको हो।","language":"ne"},
        {"question":"अंधेरी रानीवन, गाई हरायो खोज्न जाम् । के हो ?","options":["दुनो","जुम्रा हेरेको","आगो","चराचुरुङ्गी"],"answer":"जुम्रा हेरेको","answer_en":"जुम्रा हेरेको","explanation":"कपाललाई अँध्यारो वन जस्तो मानेर जुम्रा खोज्नु गाई खोजेजस्तो भनिएको हो।","language":"ne"},
        {"question":"अध्यारामा बस्ने भुत्री बूढी, बिहानै उठेर लुटुपुटु गर्छ । के हो ?","options":["बादल","पोतेको","नाकको फुली","लिगलिगे"],"answer":"पोतेको","answer_en":"पोतेको","explanation":"पोतो राति शान्त हुन्छ तर बिहान चलाउँदा आवाज गर्छ।","language":"ne"},
        {"question":"अँध्यारो ओडारमा सेता जन्ती । के हो ?","options":["बोक्चो","चाँदीका सिक्का","दाँत","नाक"],"answer":"दाँत","answer_en":"दाँत","explanation":"मुखलाई ओडार र दाँतलाई सेता जन्ती भनिएको हो।","language":"ne"},
        {"question":"अध्यारो कुनामा काली बूढी । के हो ?","options":["टीका","हाँडी","आँप","जुनकिरी"],"answer":"हाँडी","answer_en":"हाँडी","explanation":"भान्साको कुनामा रहेको कालो हाँडीलाई बूढीसँग तुलना गरिएको हो।","language":"ne"},
        {"question":"अँध्यारो घरमा दहीका छिटा । के हो ?","options":["चम्चा","पनिउँ","चाँदीका सिक्का","पोतो"],"answer":"चाँदीका सिक्का","answer_en":"चाँदीका सिक्का","explanation":"अँध्यारोमा चम्किने सिक्का दहीका छिटाजस्तै देखिन्छ।","language":"ne"},
        {"question":"अँध्यारोमा देखिन्छ, उज्यालोमा छैन, जति कोसिस गरे पनि टिप्न सकिदैन । के हो ?","options":["आगो","कानुन","तारा","पोतो"],"answer":"तारा","answer_en":"तारा","explanation":"तारा राति मात्र देखिन्छ र समात्न सकिँदैन।","language":"ne"},
        {"question":"अँध्यारोमा बस्ने भुत्री बूढी, बिहान सबेरै उठेर लुटुपुटु गर्छ । के हो ?","options":["पोतो","टीका","नाइटो","गुन्द्री"],"answer":"पोतो","answer_en":"पोतो","explanation":"यो पनि पोतोसँग सम्बन्धित उखान हो, बिहान प्रयोग गर्दा आवाज गर्छ।","language":"ne"},
        {"question":"अँध्यारोमा हराउँछु, उज्यालोमा आउँछु, जता जान्छन् मेरा उनी उतैतिर धाउँछु । के हो ?","options":["टीका","थाल","कटुसको फल","छायाँ"],"answer":"छायाँ","answer_en":"छायाँ","explanation":"छायाँ उज्यालोमा देखिन्छ र मानिससँगै चल्छ।","language":"ne"},
        {"question":"अकासिदा जहाँतहीं, पातलिदा कहाँकहाँ ? के हो ?","options":["चराचुरुङ्गी","आगो","पोतेको","हाँडी"],"answer":"चराचुरुङ्गी","answer_en":"चराचुरुङ्गी","explanation":"चराहरू उड्दा फैलिन्छन् र बस्दा सानो ठाउँमा हुन्छन्।","language":"ne"},
        {"question":"अक्षर छ, किताब होइन, गोलो छ, इनार होइन, संसार डुल्छ, खुट्टा छैन। के हो ?","options":["डढेलो","पैसा","जुम्रा हेरेको","जुनकिरी"],"answer":"पैसा","answer_en":"पैसा","explanation":"पैसा गोलो हुन्छ, लेखिएको हुन्छ र संसारभर घुम्छ।","language":"ne"},
        {"question":"अक्षर छन्, पुस्तक होइन, लेख्छ, कलम होइन, टुकटुक गर्छ, घडी होइन । के हो ?","options":["बाँस","लुगा सिएको","मदुस","टाइपराइटर"],"answer":"टाइपराइटर","answer_en":"टाइपराइटर","explanation":"टाइपराइटरले अक्षर लेख्छ र आवाज निकाल्छ।","language":"ne"},
        {"question":"अखेटे पखेटे गहभरि आँसु भित्र नसा बाहिर मासु । के हो ?","options":["बादल","आँप","पोतो","तारा"],"answer":"आँप","answer_en":"आँप","explanation":"आँपको बनावटलाई यसरी वर्णन गरिएको हो।","language":"ne"},
        {"question":"अगाडिको काट्दा खाने चिज हुन्छ, बीचको काट्दा सुन्ने अङ्ग बन्छ । के हो ?","options":["कानुन","चुङगम","लिगलिगे","ढिकी"],"answer":"कानुन","answer_en":"कानुन","explanation":"शब्द काट्दा अर्थ परिवर्तन हुन्छ—कान र खानसँग सम्बन्धित।","language":"ne"},
        {"question":"अगाडि शहख पछाडि पख । के हो ?","options":["एस्ट्रे","कुकुर","दाँत","नाइटो"],"answer":"कुकुर","answer_en":"कुकुर","explanation":"कुकुरको आवाज (भुक्ने) र शरीरको बनावटसँग सम्बन्धित।","language":"ne"},
        {"question":"अगाडि साइत, पुठामा लाइट। के हो ?","options":["पोतेको","छाता","कानुन","जुनकिरी"],"answer":"जुनकिरी","answer_en":"जुनकिरी","explanation":"जुनकिरीको पछाडि भागमा बत्ती जस्तो उज्यालो हुन्छ।","language":"ne"},
        {"question":"अगाडि हिँड्छ, पछाडि बाटो थुन्छ । के हो ?","options":["दुनो","लुगा सिएको","हाँडी","कानुन"],"answer":"लुगा सिएको","answer_en":"लुगा सिएको","explanation":"सिउँदा पछाडि धागोले बाटो बन्द गर्छ।","language":"ne"},
        {"question":"अगाडि हिँड्दो, पछाडि बाटो थुन्दो । के हो ?","options":["कटुसको फल","पैसा","सियो र धागो","दुनो"],"answer":"सियो र धागो","answer_en":"सियो र धागो","explanation":"सियोले अगाडि बाटो बनाउँछ, धागोले पछाडि बन्द गर्छ।","language":"ne"},
        {"question":"अगाडि हेर्दा देखिन्छ, पछाडि हेर्दा देखिन्न । के हो ?","options":["टीका","फर्सी","ऐना","पैसा"],"answer":"ऐना","answer_en":"ऐना","explanation":"ऐनाले अगाडिको मात्र प्रतिबिम्ब देखाउँछ।","language":"ne"},
        {"question":"अगेनी, चुलो कुनै होइन, अगुल्टो ल्याई जोत्छन्, सफासुग्घर अनुहारमा खरानीले पोत्छन् । के हो ?","options":["थैली","एस्ट्रे","आगो","चाँदीका सिक्का"],"answer":"एस्ट्रे","answer_en":"एस्ट्रे","explanation":"चुरोटको खरानी राख्ने भाँडोलाई यसरी तुलना गरिएको हो।","language":"ne"},
        {"question":"अग्लो चुलीको एउटा पाखामा एक थुंगा फूल । के हो ?","options":["हाँडी","छायाँ","नाकको फुली","तारा"],"answer":"नाकको फुली","answer_en":"नाकको फुली","explanation":"नाकलाई चुली र फुलीलाई फूलसँग तुलना गरिएको हो।","language":"ne"},
        {"question":"अग्लो डाँडामा दुईवटा सुरुङ । के हो ?","options":["नाक","कटुसको फल","दुनो","थैली"],"answer":"नाक","answer_en":"नाक","explanation":"नाकको दुई प्वाललाई सुरुङ भनिएको हो।","language":"ne"},
        {"question":"अग्लो देखिन्छ, धरहरा होइन, निहुरिन्छ बेहुली होइन । के हो ?","options":["बाँस","डढेलो","कुकुर","घुडा"],"answer":"बाँस","answer_en":"बाँस","explanation":"बाँस अग्लो हुन्छ र हावामा निहुरिन्छ।","language":"ne"},
        {"question":"अग्लो पहरामा एउटा खुड्किलो । के हो ?","options":["चराचुरुङ्गी","पोतेको","नाइटो","किताब"],"answer":"नाइटो","answer_en":"नाइटो","explanation":"पेटको नाइटोलाई पहराको खुड्किलोसँग तुलना गरिएको हो।","language":"ne"},
        {"question":"अग्लो पहरामा गुराँस फुलेको । के हो ?","options":["कुकुर भुकेको","नाक","टीका","हाँडी"],"answer":"टीका","answer_en":"टीका","explanation":"निधारमा लगाइएको टीकालाई गुराँस फूलसँग तुलना गरिएको हो।","language":"ne"},
        {"question":"अग्लो पहरामा चहै चहे गर्ने । के हो ?","options":["मौरी","दाँत","लिगलिगे","छाता"],"answer":"लिगलिगे","answer_en":"लिगलिगे","explanation":"टाउकोको कपालमा बस्ने किरा (लिगलिगे) को व्यवहारलाई जनाइएको हो।","language":"ne"},
        {"question":"अग्लो भीरमा भेडा थुप्रिएका । के हो ?","options":["पोतेको","डाडु","अक्षताको टीका","मदुस"],"answer":"अक्षताको टीका","answer_en":"अक्षताको टीका","explanation":"निधारमा लगाइएको अक्षता भेडा जस्तो देखिन्छ।","language":"ne"},
        {"question":"अग्लो रूखमा एउटा खोचे पात । के हो ?","options":["लिगलिगे","डाडु","हाँडी","आगो"],"answer":"डाडु","answer_en":"डाडु","explanation":"भान्सामा प्रयोग हुने डाडुको बनावटलाई यसरी वर्णन गरिएको हो।","language":"ne"},
        {"question":"अग्लो रुखमा एउटै पात । के हो ?","options":["छायाँ","पोतो","पनिउँ","लिगलिगे"],"answer":"पनिउँ","answer_en":"पनिउँ","explanation":"पनिउँ (भान्साको सामान) को आकृतिलाई रुख र पातसँग तुलना गरिएको हो।","language":"ne"},
        {"question":"अघिअघि महादेव, पछिपछि जन्ती । के हो ?","options":["पोतेको","मौरी","हाँडी","कुकुर"],"answer":"मौरी","answer_en":"मौरी","explanation":"मौरी वा केरा पसाउने क्रममा अगाडि–पछाडि लाग्ने समूहलाई जनाइएको हो।","language":"ne"},
        {"question":"अघिअघि रतुवा पछिपछि कलुवा । के हो ?","options":["एस्ट्रे","लुगा सिएको","जुनकिरी","डढेलो"],"answer":"डढेलो","answer_en":"डढेलो","explanation":"आगो फैलिँदा अगाडि रातो र पछाडि कालो देखिन्छ।","language":"ne"},
        {"question":"अघिअघि शङ्ख बज्छ, पछिपछि ध्वजा हल्लन्छ । के हो ?","options":["टाइपराइटर","जुनकिरी","कुकुर भुकेको","कानुन"],"answer":"कुकुर भुकेको","answer_en":"कुकुर भुकेको","explanation":"कुकुर भुक्दा आवाज (शङ्ख) र पुच्छर हल्लाउने (ध्वजा) सँग तुलना गरिएको हो।","language":"ne"},
        {"question":"अधिपछि अगाउने, चाडवाडमा भोकाउने । के हो ?","options":["कटुसको फल","मदुस","हाँडी","बाँस"],"answer":"मदुस","answer_en":"मदुस","explanation":"सामान राख्ने बाकस दैनिक प्रयोगमा भरिन्छ तर चाडपर्वमा खाली हुन्छ।","language":"ne"},
        {"question":"अघिपछि आको आँ, खाने बेला मुख च्याप्प । के हो ?","options":["नङकट","मदुस","किताब","टाइपराइटर"],"answer":"नङकट","answer_en":"नङकट","explanation":"चिम्टाले समाउँदा मुख जस्तो भाग बन्द हुन्छ।","language":"ne"},
        {"question":"अधिपछि खाने, चाडवाडमा भोकै । के हो ?","options":["बोक्चो","कुकुर","थाल","बादल"],"answer":"बोक्चो","answer_en":"बोक्चो","explanation":"सामान्य समयमा प्रयोग हुन्छ तर चाडपर्वमा कम प्रयोग हुन्छ।","language":"ne"},
        {"question":"अधिपछि गुटमुटिएर बस्ने, पाहुना आएपछि उत्तानो परेर सुत्ने । के हो ?","options":["गुन्द्री","हाँडी","तारा","कानुन"],"answer":"गुन्द्री","answer_en":"गुन्द्री","explanation":"गुन्द्री मोडेर राखिन्छ र पाहुना आएपछि ओछ्याइन्छ।","language":"ne"},
        {"question":"अघिपछि जुँगे दाइ मुख खुम्च्याई बस्छ, जुँगा तानेपछि मुख बाई हाँस्छ । के हो ?","options":["थाल","लुगा सिएको","पोतो","थैली"],"answer":"थैली","answer_en":"थैली","explanation":"थैली बन्द हुँदा मुख खुम्चिएको जस्तो हुन्छ, खोल्दा खुल्छ।","language":"ne"},
        {"question":"अधिपछि चिल्लो, चाडवाडमा फुस्रो । के हो ?","options":["कुकुर भुकेको","कटुसको फल","ढिकी","दुनो"],"answer":"ढिकी","answer_en":"ढिकी","explanation":"दैनिक प्रयोगमा चिल्लो हुन्छ, चाडपर्वमा कम प्रयोग हुँदा फुस्रो हुन्छ।","language":"ne"},
        {"question":"अघिपछि पेटभरि खान्छ, चाडवाडमा भोकै पर्छ । के हो ?","options":["अक्षताको टीका","बोक्चो","आँप","तारा"],"answer":"बोक्चो","answer_en":"बोक्चो","explanation":"सामान्य समयमा धेरै प्रयोग हुने तर चाडपर्वमा कम प्रयोग हुने वस्तु।","language":"ne"},
        {"question":"अघि बढ्दै छ, पोको छोड्दै छ । के हो ?","options":["गुन्द्री","बादल","फर्सी","कुकुर भुकेको"],"answer":"फर्सी","answer_en":"फर्सी","explanation":"फर्सी बढ्दै जाँदा बोटबाट छुट्टिँदै जाने अवस्थालाई जनाइएको हो।","language":"ne"},
        {"question":"केटीहरुको त्यो कुन चिज हो जुन दुई वटा खुट्टाको बीचमा हुन्छ ?","options":["घुडा","छाता","मौरी","ऐना"],"answer":"घुडा","answer_en":"घुडा","explanation":"दुवै खुट्टाको बीचमा घुडा (घुँडा) हुन्छ।","language":"ne"},
        {"question":"मुखमा हाल्न अघि कडा हुन्छ पछि नरम । के हो ?","options":["तारा","आगो","चुङगम","चाँदीका सिक्का"],"answer":"चुङगम","answer_en":"चुङगम","explanation":"चुइङगम मुखमा हाल्दा कडा हुन्छ तर चपाउँदा नरम हुन्छ।","language":"ne"},
        {"question":"अरुलाई पेट भरि खुवाउने आफु भोक्कै । के हो ?","options":["चम्चा","चराचुरुङ्गी","थाल","नाकको फुली"],"answer":"चम्चा","answer_en":"चम्चा","explanation":"चम्चाले अरुलाई खुवाउँछ तर आफु खाँदैन।","language":"ne"},
        {"question":"बिना प्वाख उड्छु बिना आँखा रुन्छु । के हो ?","options":["पैसा","कानुन","बादल","छायाँ"],"answer":"बादल","answer_en":"बादल","explanation":"बादल बिना पखेटा उड्छ र पानी पारेर रुन्छ।","language":"ne"},
        {"question":"घाँटी छ तर टाउको छैन, पेट छ तर आन्द्रा छैन । के हो ?","options":["गाग्रो","तारा","कुकुर","बाँस"],"answer":"गाग्रो","answer_en":"गाग्रो","explanation":"गाग्रो (पानीको भाँडो) को घाँटी जस्तो भाग हुन्छ तर टाउको छैन, पेट छ तर आन्द्रा छैन।","language":"ne"},
        {"question":"पात छ रुख होइन ज्ञान दिन्छ मान्छे हैन । के हो ?","options":["ऐना","पोतो","डाडु","किताब"],"answer":"किताब","answer_en":"किताब","explanation":"किताबको पाता हुन्छ तर रुख होइन, ज्ञान दिन्छ तर मान्छे होइन।","language":"ne"},
        {"question":"एक खुट्टे नानी पानी पर्दा रुने । के हो ?","options":["पोतेको","छाता","टाइपराइटर","हाँडी"],"answer":"छाता","answer_en":"छाता","explanation":"छाता एक खुट्टाको हुन्छ र पानी पर्दा खोलिन्छ।","language":"ne"},
        {"question":"वरिपरि डिल माझमा टार काम सकिने बित्तिकै नुहाउन हतार । के हो ?","options":["ऐना","चम्चा","गाग्रो","थाल"],"answer":"थाल","answer_en":"थाल","explanation":"थालमा खाना खाएपछि तुरुन्तै माझ्नुपर्छ।","language":"ne"},
        {"question":"पहिले रातो पानी खाएपछि कालो । के हो ?","options":["दुनो","नाकको फुली","घुडा","आगो"],"answer":"आगो","answer_en":"आगो","explanation":"आगो पहिले रातो हुन्छ, पानी खाएपछि (निभेपछि) कालो हुन्छ।","language":"ne"},
    ]

    if topic == 'nepali_riddles':
        selected = random.sample(GAU_KHANE_KATHA, min(count, len(GAU_KHANE_KATHA)))
        random.shuffle(selected)
        NE_TAUNTS_C = ["ओहो तिमीले सही जवाफ दियौ? आज मौसम बदली भयो कि क्या हो? 🌤️", "सही! तिम्रो यो सफलता ऐतिहासिक क्षण हो, रेकर्ड गर 📹", "वाह! तिमीले यो त मिलाइहाल्यौ — संयोगले भए पनि 🎲", "ए भाइ सही त भयो तर यति खुशी नहोऊ अर्को पनि छ 😅", "गज्जब! यो तिम्रो दिन हो क्यारे ☀️", "सही जवाफ! अब तिमी जीनियस भइहाल्यौ है? 🧠", "ओह! आज त तिम्रो स्कोर ब्याङ्क ब्यालेन्स भन्दा पनि माथि छ 📈", "सही! म तिम्रो IQ १० प्वाइन्टले बढाउँदै छु अहिले 🔋", "तिमीले सही मिलायौ भन्या, अब घुमाउन पाइन्छ? 🎉", "यत्तिकै हो तिमीले जिन्दगीमा केही बिगारेका छैनौ यार 💪"]
        NE_TAUNTS_W = ["तिम्रो दिमाग पनि यस्तै छ — खाली 😂", "यति सजिलो पनि आएन? आज त घुमाइयो 🌀", "Timi ta master nai raichau — mastering the art of being wrong 🏆", "यो प्रश्न त बच्चाले पनि मिलाउँछ तिमी बाहेक 👶", "Bro read a book... any book 📚", "तिमी त titau नै हौ 🤡", "Congratulations, you played yourself 🏆🤡", "गलत जवाफ — सही जवाफको छिमेकी पनि होइन 💀", "Timi ra yo question ko love story — one sided ❤️‍🩹", "Aru kehi kaam gara bro, yesto khelauna napaiyo 🎮", "यो क्विज तिम्रो लागि होइन, घर जाऊ 🏠", "MCQ ma ni fail? Pack it up 🧳", "Brain: 404 not found 💻", "तिमीले guess गर्दा पनि हारेको — double defeat 🥇🥇", "Ghar ma bau lai bhanchu hai, padhau yar lai एक पटक 😤", "Tanab nabau, life ma aru pani option chaina timro lagi 🎯", "तिमी त champion nai raichau... of getting it wrong 🏆", "Bro thought he cooked but he just burnt water 🍳🔥", "तिम्रो IQ यो question भन्दा पनि कम छ 📉", "यति सजिलो प्रश्नको जवाफ नदिने मान्छे संसारमा तिमी मात्र होला 😂"]
        for q in selected:
            if 'taunt_correct' not in q or not q['taunt_correct']:
                q['taunt_correct'] = random.choice(NE_TAUNTS_C)
            if 'taunt_wrong' not in q or not q['taunt_wrong']:
                q['taunt_wrong'] = q.get('taunt') or random.choice(NE_TAUNTS_W)
            q.pop('taunt', None)
        return JsonResponse({"questions": selected})

    # Hardcoded English riddles — all from real riddle videos
    RIDDLES_EN = [
        {"question": "What is the world's laziest mountain?", "options": ["Mount Everest", "Mount Fuji", "K2", "Kilimanjaro"], "answer": "Mount Everest", "answer_en": "Mount Everest", "explanation": "It is Everest (ever-rest). Because it's always resting.", "taunt": "Get it? Ever-rest? ... I'll see myself out 🚪", "language": "en"},
        {"question": "What do you get if you put a radio in the fridge?", "options": ["Cool music", "Cold news", "Frozen beats", "Icy tunes"], "answer": "Cool music", "answer_en": "cool music", "explanation": "The radio gets cold, so you get cool music.", "language": "en"},
        {"question": "How can a man go 8 days without sleep?", "options": ["He sleeps at night", "He takes naps", "He drinks coffee", "He's a robot"], "answer": "He sleeps at night", "answer_en": "he sleeps at night", "explanation": "He goes 8 days without sleep by sleeping at night — the days are when he's awake!", "language": "en"},
        {"question": "What two things can you never eat for breakfast?", "options": ["Lunch and dinner", "Eggs and toast", "Cereal and milk", "Fruit and yogurt"], "answer": "Lunch and dinner", "answer_en": "lunch and dinner", "explanation": "You can't eat lunch and dinner for breakfast — they're different meals!", "language": "en"},
        {"question": "How do you divide 8 apples among 9 people without cutting?", "options": ["Make applesauce", "Juice them", "Bake a pie", "Give 8 people apples"], "answer": "Make applesauce", "answer_en": "make applesauce", "explanation": "When you make applesauce, everyone can have some without cutting the apples.", "language": "en"},
        {"question": "How do you know carrots are good for your eyes?", "options": ["Rabbits never wear glasses", "Carrots are orange", "They have vitamin A", "Doctor said so"], "answer": "Rabbits never wear glasses", "answer_en": "rabbits never wear glasses", "explanation": "If carrots weren't good for eyes, rabbits would need glasses!", "taunt": "When's the last time you saw a bunny in bifocals? Exactly 🐰", "language": "en"},
        {"question": "When does a British potato change its nationality?", "options": ["When it becomes French fries", "When it travels", "When it's boiled", "When it's mashed"], "answer": "When it becomes French fries", "answer_en": "when it becomes french fries", "explanation": "A British potato becomes French when it turns into French fries.", "language": "en"},
        {"question": "What does a cat have that no other animal has?", "options": ["Kittens", "Whiskers", "A tail", "Nine lives"], "answer": "Kittens", "answer_en": "kittens", "explanation": "Only a cat has kittens — baby cats!", "language": "en"},
        {"question": "What is orange and sounds like a parrot?", "options": ["A carrot", "An orange", "A pumpkin", "A goldfish"], "answer": "A carrot", "answer_en": "a carrot", "explanation": "Carrot sounds like 'carrot' which is close to 'parrot' — both end with 'rrot'!", "language": "en"},
        {"question": "Why did the man bury his torch?", "options": ["The batteries were dead", "He was hiding it", "He didn't need it", "It was broken"], "answer": "The batteries were dead", "answer_en": "the batteries were dead", "explanation": "He buried the torch because the batteries were dead — like a funeral!", "language": "en"},
        {"question": "What tree can you carry in your hand?", "options": ["A palm tree", "An oak tree", "A pine tree", "A banyan tree"], "answer": "A palm tree", "answer_en": "a palm tree", "explanation": "Your palm is part of your hand, so you're technically holding a palm tree!", "taunt": "You were thinking of an actual tree, weren't you? 🌴", "language": "en"},
        {"question": "You buy me to eat, but you never eat me. What am I?", "options": ["A plate", "A fork", "A table", "A recipe"], "answer": "A plate", "answer_en": "a plate", "explanation": "You buy a plate to eat food from, but you never eat the plate itself.", "language": "en"},
        {"question": "You can hold me in your left hand but not your right. What am I?", "options": ["Your right hand", "Your left hand", "A ring", "A watch"], "answer": "Your right hand", "answer_en": "your right hand", "explanation": "You can hold your right hand in your left hand, but not in your right!", "language": "en"},
        {"question": "I am a celebrity fish. What am I?", "options": ["A starfish", "A clownfish", "A goldfish", "A piranha"], "answer": "A starfish", "answer_en": "a starfish", "explanation": "A starfish is a celebrity — like a movie star!", "language": "en"},
        {"question": "I have no life, but I can die. What am I?", "options": ["A battery", "A phone", "A light bulb", "A candle"], "answer": "A battery", "answer_en": "a battery", "explanation": "A battery doesn't have life but can die (run out of power).", "language": "en"},
        {"question": "You go at red and stop at green. Who am I?", "options": ["A watermelon", "A traffic light", "A car", "A pedestrian"], "answer": "A watermelon", "answer_en": "a watermelon", "explanation": "You eat the red inside but stop at the green rind!", "taunt": "Green means stop eating, apparently 🍉", "language": "en"},
        {"question": "I'm the kind of table you can eat. What am I?", "options": ["A vegetable", "A desk", "A bench", "A counter"], "answer": "A vegetable", "answer_en": "a vegetable", "explanation": "Vege-table — it's a table you can eat (vegetables)!", "language": "en"},
        {"question": "I run but never walk. I have a bed but never sleep. What am I?", "options": ["A river", "A road", "A train", "A runner"], "answer": "A river", "answer_en": "a river", "explanation": "A river runs (flows) and has a riverbed, but never sleeps.", "language": "en"},
        {"question": "I jump when I walk and sit when I stand. What am I?", "options": ["A kangaroo", "A frog", "A rabbit", "A grasshopper"], "answer": "A kangaroo", "answer_en": "a kangaroo", "explanation": "A kangaroo jumps as it moves and sits on its hind legs when standing.", "language": "en"},
        {"question": "I have one foot but no legs. What am I?", "options": ["A ruler", "A snake", "A snail", "A fish"], "answer": "A ruler", "answer_en": "a ruler", "explanation": "A ruler has one 'foot' (unit of measurement) but no legs.", "language": "en"},
        {"question": "What do you call a poodle in the summertime?", "options": ["A hot dog", "A wet dog", "A cool pup", "A summer pooch"], "answer": "A hot dog", "answer_en": "a hot dog", "explanation": "A poodle in summer is a hot dog — because it's hot out and it's a dog!", "language": "en"},
        {"question": "If I drink, I die. If I eat, I grow. What am I?", "options": ["Fire", "A plant", "A human", "A candle"], "answer": "Fire", "answer_en": "fire", "explanation": "Water kills fire, but fuel (food) makes it grow.", "language": "en"},
        {"question": "Why don't elephants use computers?", "options": ["They're scared of the mouse", "They have big trunks", "They can't type", "They prefer phones"], "answer": "They're scared of the mouse", "answer_en": "theyre scared of the mouse", "explanation": "Elephants are afraid of a computer mouse!", "taunt": "Even elephants know better than to click suspicious links 🐘", "language": "en"},
        {"question": "You find this in Earth, Jupiter, Mercury, and Mars but not Venus or Neptune. What am I?", "options": ["The letter R", "Water", "Atmosphere", "Mountains"], "answer": "The letter R", "answer_en": "the letter r", "explanation": "The letter 'R' appears in Earth, Jupiter, Mercury, and Mars but not in Venus or Neptune.", "language": "en"},
        {"question": "You are my brother, but I am not your brother. What am I?", "options": ["Your sister", "Your cousin", "Your father", "Your uncle"], "answer": "Your sister", "answer_en": "your sister", "explanation": "I am your sister — you are my brother, but I am not your brother, I'm your sister.", "language": "en"},
        {"question": "I am always in front of you but you'll never see me. What am I?", "options": ["The future", "The past", "Your nose", "The air"], "answer": "The future", "answer_en": "the future", "explanation": "The future is always ahead of you, but you can never see it.", "language": "en"},
        {"question": "Two boys are born at the same time to the same mom but aren't twins. How?", "options": ["They're triplets", "They're adopted", "One is older", "Different fathers"], "answer": "They're triplets", "answer_en": "theyre triplets", "explanation": "They are two of triplets — there's a third sibling making them triplets, not twins.", "taunt": "The third triplet is probably the smartest one too 🧠", "language": "en"},
        {"question": "I am a color but you can also eat me. What am I?", "options": ["Orange", "Apple", "Banana", "Grape"], "answer": "Orange", "answer_en": "orange", "explanation": "Orange is both a color and a fruit you can eat.", "language": "en"},
        {"question": "I have branches but no trunk, leaves, or fruit. What am I?", "options": ["A bank", "A tree", "A river", "A road"], "answer": "A bank", "answer_en": "a bank", "explanation": "A bank has branches (locations) but no tree trunk, leaves, or fruit.", "language": "en"},
        {"question": "I have keys but no doors. What am I?", "options": ["A piano", "A map", "A computer", "A lock"], "answer": "A piano", "answer_en": "a piano", "explanation": "A piano has musical keys but no doors to unlock.", "language": "en"},
        {"question": "What always ends everything?", "options": ["The letter G", "The letter E", "Death", "Time"], "answer": "The letter G", "answer_en": "the letter g", "explanation": "The word 'everything' ends with G.", "language": "en"},
        {"question": "I have ears but can't hear. What am I?", "options": ["Corn", "A statue", "A phone", "A robot"], "answer": "Corn", "answer_en": "corn", "explanation": "Corn has ears (the part you eat) but can't hear anything.", "language": "en"},
        {"question": "Before Mount Everest was discovered, what was the highest mountain?", "options": ["Mount Everest", "K2", "Denali", "Kilimanjaro"], "answer": "Mount Everest", "answer_en": "mount everest", "explanation": "Mount Everest was still the highest — it just wasn't discovered yet!", "taunt": "Everest was minding its own business being tall 🤫🗻", "language": "en"},
        {"question": "What's always on the ground but never dirty?", "options": ["A shadow", "The floor", "Grass", "Carpet"], "answer": "A shadow", "answer_en": "a shadow", "explanation": "A shadow stays on the ground but never gets dirty.", "language": "en"},
        {"question": "What has many rings but no fingers?", "options": ["A phone", "A tree", "A finger", "A necklace"], "answer": "A phone", "answer_en": "a phone", "explanation": "A phone has many ringtones (rings) but no fingers.", "language": "en"},
        {"question": "David's parents have three sons: Snap, Crackle, and who?", "options": ["David", "Pop", "Snap Jr.", "Mike"], "answer": "David", "answer_en": "david", "explanation": "The third son is David — the riddle is about David's own family!", "language": "en"},
        {"question": "I am yellow, long, and monkeys love me. What am I?", "options": ["A banana", "A corn", "A pineapple", "A lemon"], "answer": "A banana", "answer_en": "a banana", "explanation": "Bananas are yellow, long, and monkeys love them.", "language": "en"},
        {"question": "I have a head but no brain. What am I?", "options": ["Lettuce", "A pin", "A nail", "A doll"], "answer": "Lettuce", "answer_en": "lettuce", "explanation": "Lettuce has a head (head of lettuce) but no brain.", "language": "en"},
        {"question": "Which letter can make honey?", "options": ["B (bee)", "H", "A", "C"], "answer": "B (bee)", "answer_en": "b bee", "explanation": "The letter B sounds like 'bee', which makes honey!", "language": "en"},
        {"question": "In which month do people sleep the least?", "options": ["February", "January", "December", "March"], "answer": "February", "answer_en": "february", "explanation": "February has the fewest days, so people sleep less in that month overall.", "taunt": "Short month, short answers, short patience 😤", "language": "en"},
        {"question": "What has a head and a tail but no body?", "options": ["A coin", "A snake", "A pencil", "A rope"], "answer": "A coin", "answer_en": "a coin", "explanation": "A coin has 'heads' and 'tails' sides but no body.", "language": "en"},
        {"question": "If you throw a black stone into the Red Sea, what does it become?", "options": ["Wet", "Red", "Black", "Sinking"], "answer": "Wet", "answer_en": "wet", "explanation": "Any stone thrown into water becomes wet — color doesn't matter!", "language": "en"},
        {"question": "What has many teeth but can't bite?", "options": ["A comb", "A saw", "A zipper", "A shark"], "answer": "A comb", "answer_en": "a comb", "explanation": "A comb has teeth for grooming hair but can't bite.", "language": "en"},
        {"question": "I start with E and end with E. I have strong countries inside me.", "options": ["Europe", "England", "Egypt", "Energy"], "answer": "Europe", "answer_en": "europe", "explanation": "Europe starts with E, ends with E, and contains many strong countries.", "language": "en"},
        {"question": "What did the ocean say to the sand?", "options": ["Nothing, it just waved", "Hello", "Goodbye", "Move over"], "answer": "Nothing, it just waved", "answer_en": "nothing it just waved", "explanation": "The ocean waved (wave action) without saying anything.", "language": "en"},
        {"question": "I fly without wings and cry without eyes. What am I?", "options": ["A cloud", "A bird", "A plane", "The wind"], "answer": "A cloud", "answer_en": "a cloud", "explanation": "Clouds fly (float) in the sky and cry (rain) without eyes or wings.", "language": "en"},
        {"question": "What is harder to catch the faster you run?", "options": ["Your breath", "A bus", "Time", "A cheetah"], "answer": "Your breath", "answer_en": "your breath", "explanation": "The faster you run, the harder it is to catch your breath.", "language": "en"},
        {"question": "I'm a seed with three letters. Remove the last two and I still sound the same.", "options": ["Pea (P)", "Bee", "Corn", "Nut"], "answer": "Pea (P)", "answer_en": "pea p", "explanation": "Pea spelled P-E-A. Remove E-A, you get P — still sounds like 'pea'!", "language": "en"},
        {"question": "What's the quickest way to double your money?", "options": ["Put it in front of a mirror", "Invest it", "Save it", "Trade it"], "answer": "Put it in front of a mirror", "answer_en": "put it in front of a mirror", "explanation": "A mirror shows a reflection, doubling what you see — including money!", "language": "en"},
        {"question": "I'm first on earth, second in heaven. I appear twice a week and once a year.", "options": ["The letter E", "The letter A", "The letter I", "The letter O"], "answer": "The letter E", "answer_en": "the letter e", "explanation": "E is first in 'earth', second in 'heaven', appears twice in 'week', once in 'year'.", "taunt": "E for effort? More like E for 'everyone got it but you' 💀", "language": "en"},
        {"question": "The more you encounter, the less you can see.", "options": ["Darkness", "Light", "Fog", "Smoke"], "answer": "Darkness", "answer_en": "darkness", "explanation": "The darker it gets, the less you can see.", "language": "en"},
        {"question": "I have a shell but I am not an egg. What am I?", "options": ["A turtle", "A snail", "A nut", "A crab"], "answer": "A turtle", "answer_en": "a turtle", "explanation": "A turtle has a hard shell on its back but isn't an egg.", "language": "en"},
        {"question": "What has words but never speaks?", "options": ["A book", "A letter", "A sign", "A phone"], "answer": "A book", "answer_en": "a book", "explanation": "A book has written words but can't speak them aloud.", "language": "en"},
        {"question": "Which word becomes shorter when you add two letters?", "options": ["Short", "Small", "Tiny", "Brief"], "answer": "Short", "answer_en": "short", "explanation": "Add 'er' to 'short' and you get 'shorter' — it literally becomes shorter!", "language": "en"},
        {"question": "What question can you never say yes to?", "options": ["Are you asleep?", "Is the sky blue?", "Do you exist?", "Are you hungry?"], "answer": "Are you asleep?", "answer_en": "are you asleep", "explanation": "If you're awake enough to say yes, you're not asleep!", "language": "en"},
        {"question": "I twinkle at night but I'm not a light. What am I?", "options": ["A star", "A firefly", "A moon", "A diamond"], "answer": "A star", "answer_en": "a star", "explanation": "Stars twinkle in the night sky but aren't artificial lights.", "language": "en"},
        {"question": "I am in 'life' but not in 'death'. You can't have fun without me.", "options": ["The letter F", "The letter L", "Fun", "Smile"], "answer": "The letter F", "answer_en": "the letter f", "explanation": "F is in 'life' and 'fun' but not in 'death'. You can't have 'fun' without F!", "language": "en"},
        {"question": "I'm an insect whose first part is the name of another insect.", "options": ["A beetle (bee)", "A butterfly", "A dragonfly", "A grasshopper"], "answer": "A beetle (bee)", "answer_en": "a beetle bee", "explanation": "Beetle starts with 'bee' (B) which is also an insect!", "language": "en"},
        {"question": "A blind man lost his phone, cap, and bag. What did he lose first?", "options": ["His sight", "His phone", "His memory", "His way"], "answer": "His sight", "answer_en": "his sight", "explanation": "He lost his sight first — that's why he's blind!", "taunt": "That one was dark — literally 🌑", "language": "en"},
        {"question": "What's an astronaut's favorite key on the keyboard?", "options": ["Space bar", "Enter", "Shift", "Tab"], "answer": "Space bar", "answer_en": "space bar", "explanation": "An astronaut loves space — so the space bar is their favorite!", "language": "en"},
        {"question": "I start green, turn yellow, and taste mellow. What am I?", "options": ["A mango", "A banana", "A papaya", "A pineapple"], "answer": "A mango", "answer_en": "a mango", "explanation": "Mangoes start green and turn yellow when ripe, tasting sweet and mellow.", "language": "en"},
        {"question": "What can fill a room without taking up any space?", "options": ["Light", "Sound", "Air", "Smell"], "answer": "Light", "answer_en": "light", "explanation": "Light fills every corner of a room but takes up no physical space.", "language": "en"},
        {"question": "The more you chase me, the faster I run. What am I?", "options": ["The wind", "A dream", "A thief", "Time"], "answer": "The wind", "answer_en": "the wind", "explanation": "You can't catch the wind — the more you chase it, the faster it seems to go.", "language": "en"},
        {"question": "You can catch me but you can't throw me. What am I?", "options": ["A cold", "A ball", "A fish", "A bus"], "answer": "A cold", "answer_en": "a cold", "explanation": "You can catch a cold (get sick) but you can't throw it!", "language": "en"},
        {"question": "Who has married many women but was never married?", "options": ["A priest", "A playboy", "A king", "A bachelor"], "answer": "A priest", "answer_en": "a priest", "explanation": "A priest marries many couples but may never be married himself.", "language": "en"},
        {"question": "I sound like one letter but am written with three. You look through me.", "options": ["An eye", "A window", "Glasses", "A lens"], "answer": "An eye", "answer_en": "an eye", "explanation": "Eye sounds like 'I' (one letter), is spelled with 3 letters, and you see through it.", "taunt": "I see what you did there... or did you? 👁️", "language": "en"},
        {"question": "I have thousands of wheels but I'm not a car. What am I?", "options": ["A train", "A plane", "A bike", "A truck"], "answer": "A train", "answer_en": "a train", "explanation": "A train has many wheels rolling along the tracks.", "language": "en"},
        {"question": "I go up but never come down. What am I?", "options": ["Age", "A balloon", "A plane", "Smoke"], "answer": "Age", "answer_en": "age", "explanation": "Your age always goes up and never comes down!", "language": "en"},
        {"question": "I can only be seen with the mind, not the eyes. What am I?", "options": ["An idea", "A dream", "A memory", "A thought"], "answer": "An idea", "answer_en": "an idea", "explanation": "Ideas exist in the mind and can't be physically seen with eyes.", "language": "en"},
        {"question": "I become smaller every time I take a bath. What am I?", "options": ["A bar of soap", "A sponge", "An ice cube", "A towel"], "answer": "A bar of soap", "answer_en": "a bar of soap", "explanation": "Soap shrinks as you use it — the more baths it takes, the smaller it gets.", "language": "en"},
        {"question": "I'm a fruit and a tech brand. What am I?", "options": ["Apple", "BlackBerry", "Orange", "Mango"], "answer": "Apple", "answer_en": "apple", "explanation": "Apple is both a fruit and the name of a famous tech company.", "language": "en"},
        {"question": "What time of day is spelled the same forwards and backwards?", "options": ["Noon", "Midnight", "Midday", "Eleven"], "answer": "Noon", "answer_en": "noon", "explanation": "Noon — n-o-o-n — reads the same forwards and backwards (a palindrome).", "language": "en"},
        {"question": "What belongs to you but other people use it more?", "options": ["Your name", "Your phone", "Your house", "Your car"], "answer": "Your name", "answer_en": "your name", "explanation": "Other people say your name more often than you do!", "language": "en"},
        {"question": "I am a bird, a fruit, and a person. What am I?", "options": ["Kiwi", "Robin", "Jay", "Swan"], "answer": "Kiwi", "answer_en": "kiwi", "explanation": "Kiwi is a bird (flightless), a fruit (kiwifruit), and a nickname for New Zealanders.", "taunt": "Bet you only knew one of those. Maybe zero? 🥝", "language": "en"},
        {"question": "What can speak but has no mouth? Reproduce but no body?", "options": ["An echo", "A parrot", "A robot", "A phone"], "answer": "An echo", "answer_en": "an echo", "explanation": "An echo repeats (speaks) your words but has no mouth or body.", "language": "en"},
        {"question": "A house with all 4 walls facing south. A bear walks by. What color?", "options": ["White", "Brown", "Black", "Polar pattern"], "answer": "White", "answer_en": "white", "explanation": "The house is at the North Pole (only place where all walls face south). So it's a polar bear — white!", "language": "en"},
        {"question": "The more you take, the more you leave behind. What am I?", "options": ["Footsteps", "Money", "Time", "Memories"], "answer": "Footsteps", "answer_en": "footsteps", "explanation": "Each step you take leaves a footprint behind — more steps = more footprints.", "language": "en"},
        {"question": "I'm weightless but put me in a bucket and it gets lighter. What am I?", "options": ["A hole", "Air", "A feather", "Light"], "answer": "A hole", "answer_en": "a hole", "explanation": "Adding a hole removes material from the bucket, making it lighter.", "language": "en"},
        {"question": "I have cities but no houses, mountains but no trees, water but no fish.", "options": ["A map", "A globe", "A painting", "A book"], "answer": "A map", "answer_en": "a map", "explanation": "A map shows cities, mountains, and water but they're just symbols, not real.", "language": "en"},
        {"question": "What must be broken before you can use it?", "options": ["An egg", "A pencil", "A phone", "A lock"], "answer": "An egg", "answer_en": "an egg", "explanation": "You have to crack (break) an egg before you can cook with it.", "language": "en"},
        {"question": "What comes at the end of the alphabet?", "options": ["The letter T", "The letter Z", "A period", "Omega"], "answer": "The letter T", "answer_en": "the letter t", "explanation": "The word 'alphabet' ends with the letter T.", "language": "en"},
        {"question": "I don't cry when you cut me, but you do. What am I?", "options": ["An onion", "A cake", "A paper", "A tomato"], "answer": "An onion", "answer_en": "an onion", "explanation": "An onion makes you cry when you cut it, but the onion itself doesn't cry.", "language": "en"},
    ]

    if topic == 'riddles':
        selected = random.sample(RIDDLES_EN, min(count, len(RIDDLES_EN)))
        random.shuffle(selected)
        EN_TAUNTS_C = ["Wow you got it right? Mark the calendar 📅", "Correct! I'm genuinely shocked. Good job 🎉", "Right answer! Was that luck or skill? Let's assume luck 🍀", "You got one right? Someone get this person a trophy 🏆", "Correct! The monkey on a typewriter approach works sometimes 🐒", "Nice one! Even a broken clock is right twice a day ⏰", "You answered correctly. This is NOT a drill! 🚨", "Right! I'd clap but I'm busy judging you 👏", "Congrats! You're now in the top 50% of players 🥈", "You got it! Don't let it go to your head... too late 🎈"]
        EN_TAUNTS_W = ["That was your best guess? 💀", "Bro read a book... any book 📚", "Congratulations, you played yourself 🏆🤡", "Brain: 404 not found 💻", "You thought you cooked but you just burnt water 🍳🔥", "Your IQ just dropped reading that answer 📉", "MCQ mode? More like MCQ-wned 💀", "I'd explain it but I left my crayons at home 🖍️", "Right answer is right there... and you still missed it 👀", "Pack it up, this quiz isn't for you 🧳", "Even a broken clock is right twice a day — not you though ⏰", "Your answer is like a haircut — completely wrong all over 💇", "That take was colder than Antarctica 🥶", "My grandma answers better and she's not even here 👵", "You really said 'let me try my luck'... and lost 🎲", "The right answer is waving at you — wave back 👋", "You vs correct answer: not even close 📏", "Speedrun of wrong answers any% WR 🏃💨", "Tf was that answer 💀🔥", "Out of all the options, you picked the wrong one. Impressive consistency 👏"]
        for q in selected:
            if 'taunt_correct' not in q or not q['taunt_correct']:
                q['taunt_correct'] = random.choice(EN_TAUNTS_C)
            if 'taunt_wrong' not in q or not q['taunt_wrong']:
                q['taunt_wrong'] = q.get('taunt') or random.choice(EN_TAUNTS_W)
            q.pop('taunt', None)
        return JsonResponse({"questions": selected})

    # For remaining topics, use AI with examples

    riddle_examples = ""

    if topic in ('riddles', 'nepali_riddles'):

        riddle_examples = f"""

Here are examples of the style you must follow — funny double-meaning riddles like Nepali "Gau Khane Katha":



Example riddles (DO NOT copy these verbatim, use them as style reference):

- "त्यो कुन कोट हो जुन केटाहरूले बिहेमा लगाउन मिल्दैन?" → पेटकोट

- "त्यो कुन चीज हो जुन तपाई एक पटक मात्रै लगाउन सक्नुहुन्छ?" → डाइपर

- "त्यो कुन चीज हो जुन महिलाहरूले लगाउँछन् तर पुरुषहरूले खान्छन्?" → लिपस्टिक

- "पेटमा छ औला, सिरमा छ पत्थर" → औठी

- "त्यो कुन चीज हो जुन घाममा आउँछ तर छायामा जाँदा हराउँछ?" → पसिना

- "त्यो कुन काम हो जुन गर्ने बित्तिकै बच्चा निस्कन्छन्?" → स्कुल छुट्टी

- "बालापनमा सोझो हुन्छ, ठूलो भए बाङ्गो, सानो हुँदा लुगा लगाउँछ, ठूलो भए नाङ्गो" → बाँस

- "त्यो कुन काम हो जुन सबैले अँध्यारोमै गर्छन्?" → बत्ती बाल्ने

- "केटाहरूको त्यो कुन चीज हो जुन हरेक दिन उठाउने बसाल्ने गर्छन्?" → पैताला

- "अँध्यारोमा बसेकी रानी, टाउकोमा छ आगो, शरीरमा छ पानी" → मैनबत्ती



Rules for your {"Nepali Devnagari" if is_nepali else "English"} riddles:

- {"Write the question in Nepali (Devnagari script)." if is_nepali else "Write the question in English."}

- Use CORRECT Nepali spelling (चीज NOT चिज, छुट्टी NOT छुट्टि, etc.)

- Create completely fresh, original riddles — never repeat common riddles or the examples above

- Each riddle must have a clever double meaning or unexpected funny twist

- Make the answer surprising and funny when revealed

- Think of everyday objects, situations, body parts, or cultural references

- The double meaning can be slightly cheeky/funny but keep it decent

- Generate unique riddles every time — be creative and don't reuse patterns"""



    prompt = f"""Generate {count} {"riddles" if topic in ('riddles', 'nepali_riddles') else "multiple-choice quiz questions"} about {topic_desc}.{riddle_examples}



Each {"riddle" if topic in ('riddles', 'nepali_riddles') else "question"} MUST be a JSON object with these exact keys:

- "question": the {"riddle in Nepali Devnagari" if topic == 'nepali_riddles' else "question text"} (string)

- "options": an array of exactly 4 answer choices (strings) {"" if topic in ('riddles', 'nepali_riddles') else ""}

- "answer": the correct answer (string, must be one of the 4 options)

- "answer_en": the answer in simple English transliteration for text-input matching (string, e.g. "petticoat" for "पेटकोट")

- "explanation": a brief 1-sentence explanation of why the answer is correct (string)

- "language": "ne" for Nepali riddles, "en" for English questions{"(for Nepali riddles, write both question and options in Devnagari)" if is_nepali else ""}

- REQUIRED "taunt_correct": a playful roasting message when user gets it RIGHT (still tease them, like "Wow you got it right? Mark the calendar 📅" / "Correct! I'm shocked but ok 🎉" / "You got lucky, try the next one 🍀"). Write in the user's language (Nepali for Nepali, English otherwise).

- REQUIRED "taunt_wrong": a funny roasting taunt when user gets it WRONG (like "That was your best guess? 💀" / "Brain: 404 not found 💻" / "Bro thought he cooked but he just burnt water 🍳🔥"). Must be creative, spicy, and actually funny. Write in the user's language (Nepali for Nepali, English otherwise).



Rules:

- {"For Nepali riddles (nepali_riddles), write the question and options in Devnagari Nepali with correct spelling." if topic == 'nepali_riddles' else ""}

- Make questions decent and fun, not too easy

- Each question must have exactly 4 unique options

- The correct answer must be exactly one of the 4 options

- The "answer_en" field is key: provide a simple English transliteration so users typing in English letters can match it (e.g., "petticoat" for "पेटकोट", "lipstick" for "लिपस्टिक")

- Vary difficulty within the set

- Do NOT number the questions in the text

- Output ONLY a valid JSON array, no markdown, no prose



Example format:

[

  {{"question": "What has keys but can't open locks?", "options": ["A piano", "A keychain", "A map", "A computer"], "answer": "A piano", "answer_en": "piano", "explanation": "A piano has musical keys, not lock keys.", "taunt_correct": "You actually got that? Guess I underestimated you 🎹", "taunt_wrong": "A piano plays tunes, not your brain cells apparently 🎹💀", "language": "en"}}

]"""

    result = _groq_request([{"role": "user", "content": prompt}], model="llama3-8b-8192", temperature=0.9, max_tokens=4096)

    if not result:

        result = _groq_request([{"role": "user", "content": prompt}], temperature=0.9, max_tokens=4096)

    if not result:

        result = _gemini_request(prompt)

    if not result:

        result = _openrouter_request([{"role": "user", "content": prompt}], temperature=0.9, max_tokens=4096)

    if not result:

        return JsonResponse({"error": "AI failed to generate questions"}, status=503)



    # Parse the JSON result

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

            if not all(k in q for k in ("question", "options", "answer", "explanation")):

                raise ValueError("Missing keys")

            if len(q["options"]) != 4:

                raise ValueError("Need exactly 4 options")

            if q["answer"] not in q["options"]:

                q["answer"] = q["options"][0]  # fix if AI messes up

        random.shuffle(questions)

        return JsonResponse({"questions": questions})

    except (json.JSONDecodeError, ValueError, KeyError) as e:

        return JsonResponse({"error": f"Invalid AI response: {e}"}, status=502)


@login_required
def user_stats_json(request):
    from .models import UserGameStats
    user = request.user
    xp = user.xp
    level = user.level
    coins = user.coins
    xp_in_current = xp - (level - 1) * 1000
    xp_next_level = 1000
    progress = min(int(xp_in_current / max(xp_next_level, 1) * 100), 100)

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


@login_required
def shop_page(request):
    return render(request, 'dashboard/shop.html')

@login_required
def inventory_view(request):
    return render(request, 'dashboard/inventory.html')

@login_required
def achievement_page(request):
    from .models import Achievement, UserAchievement, Title, UserTitle
    from .achievement_views import get_level_from_xp, get_tier_for_xp, get_xp_for_level
    
    user = request.user
    user_level = get_level_from_xp(user.xp)
    user_tier = get_tier_for_xp(user.xp)
    next_xp = get_xp_for_level(user_level + 1)
    xp_to_next = next_xp - user.xp
    xp_progress = (user.xp / next_xp) * 100 if next_xp > 0 else 0
    
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


# ── CHILLX POSTS (SOCIAL) VIEWS ──

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
    user_votes = {}
    for p in posts:
        v = Vote.objects.filter(post=p, user=request.user).first()
        if v:
            user_votes[p.id] = v.value
    user_categories = CATEGORIES if not request.user.preferences else [c for c in CATEGORIES if c['id'] in request.user.preferences]
    author_ids = set(p.user.id for p in posts if p.user.id != request.user.id)
    followed_authors = set(Follow.objects.filter(follower=request.user, following_id__in=author_ids).values_list('following_id', flat=True))
    return render(request, 'dashboard/social.html', {
        'posts': posts,
        'categories': user_categories,
        'active_category': category,
        'user_votes': user_votes,
        'user_votes_json': json.dumps(user_votes),
        'followed_authors_json': json.dumps(list(followed_authors)),
    })


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
    val = 1 if val > 0 else -1
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


@login_required
def social_live(request):
    from .models import SocialPost, Vote
    post_ids = request.GET.get('ids', '')
    if not post_ids:
        return JsonResponse({'posts': {}})
    ids = [int(x) for x in post_ids.split(',') if x.isdigit()]
    posts = SocialPost.objects.filter(id__in=ids)
    user_votes = {v.post_id: v.value for v in Vote.objects.filter(post__in=posts, user=request.user)}
    return JsonResponse({'posts': {
        p.id: {
            'score': p.vote_score,
            'comments': p.comments.count(),
            'voted': user_votes.get(p.id, 0),
        } for p in posts
    }})


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


@login_required
@csrf_exempt
def search_users_api(request):
    q = request.GET.get('q', '')
    users = User.objects.filter(is_active=True)
    if q:
        users = users.filter(Q(username__icontains=q) | Q(display_name__icontains=q))
    users = users.exclude(id=request.user.id)[:20]
    data = [{
        'id': u.id,
        'username': u.display_name or u.username,
        'has_avatar': bool(u.avatar_base64),
    } for u in users]
    return JsonResponse({'users': data})


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
    req.status = 'accepted' if action == 'accept' else 'rejected'
    req.save()
    return JsonResponse({'ok': True, 'status': req.status})


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
            text_style = json.loads(text_style_raw) if text_style_raw.startswith('{') else {'style': text_style_raw}
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


# ── CHATX VIEWS ──

@login_required
def chatx_view(request):
    return render(request, 'dashboard/chatx.html', {
        'user': request.user,
    })


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


@login_required
def get_messages(request, user_id):
    msgs = Message.objects.filter(
        sender=request.user, receiver_id=user_id
    ) | Message.objects.filter(
        sender_id=user_id, receiver=request.user
    )
    msgs = msgs.order_by('timestamp')
    Message.objects.filter(sender_id=user_id, receiver=request.user, is_read=False).update(is_read=True)

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
    return JsonResponse({'messages': [serialize_msg(m) for m in msgs]})


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
    conversations = []
    for u in users:
        last_msg = Message.objects.filter(
            sender=request.user, receiver=u
        ) | Message.objects.filter(
            sender=u, receiver=request.user
        )
        last_msg = last_msg.order_by('-timestamp').first()
        unread = Message.objects.filter(sender=u, receiver=request.user, is_read=False).count()
        conversations.append({
            'user_id': u.id,
            'username': u.display_name or u.username,
            'has_avatar': bool(u.avatar_base64),
            'last_message': last_msg.content if last_msg else '',
            'last_time': last_msg.timestamp.isoformat() if last_msg else '',
            'unread': unread,
        })
    conversations.sort(key=lambda c: c['last_time'], reverse=True)
    return JsonResponse({'conversations': conversations})


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


@login_required
def chat_users(request):
    q = request.GET.get('q', '')
    users = User.objects.exclude(id=request.user.id)
    if q:
        users = users.filter(username__icontains=q) | users.filter(display_name__icontains=q)
    users = users[:20]
    return JsonResponse({'users': [{
        'id': u.id,
        'username': u.display_name or u.username,
        'has_avatar': bool(u.avatar_base64),
    } for u in users]})

# ── WebRTC Call Signaling ──
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
    if signal_type not in ('offer', 'answer', 'ice', 'end'):
        return JsonResponse({'error': 'Invalid signal type'}, status=400)
    try:
        callee = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    import logging
    logger = logging.getLogger(__name__)
    data_str = json.dumps(signal_data) if isinstance(signal_data, dict) else (signal_data if isinstance(signal_data, str) else json.dumps(signal_data))
    logger.info('CallSignal: %s -> %s type=%s len(data)=%d', request.user.id, callee.id, signal_type, len(data_str))
    CallSignal.objects.create(
        caller=request.user, callee=callee,
        signal_type=signal_type, data=data_str
    )
    return JsonResponse({'ok': True})

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

@login_required
def call_status(request, user_id):
    """Check if a call is currently active with this user."""
    from .models import CallSignal
    recent = CallSignal.objects.filter(
        caller=request.user, callee_id=user_id, signal_type='offer',
        created_at__gte=timezone.now() - timedelta(seconds=30)
    ).exists()
    return JsonResponse({'has_offer': recent})

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
    cat_map = {c['id']: c['name'] for c in CATEGORIES}
    interests = [cat_map.get(p, p) for p in (profile_user.preferences or [])]
    return render(request, 'dashboard/social_profile.html', {
        'profile_user': profile_user,
        'posts': posts,
        'stories': stories,
        'is_friend': is_friend,
        'interests': interests,
        'is_own': request.user.id == profile_user.id,
    })


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


# ── MULTIPLAYER ──

@login_required
def multiplayer_view(request):
    import json
    user_json = json.dumps({
        'id': request.user.id,
        'username': request.user.username,
        'display_name': request.user.display_name or request.user.username,
        'level': request.user.level,
    })
    return render(request, 'multiplayer.html', {'user_json': user_json})


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

    return JsonResponse({
        'room_code': room_code,
        'room': {
            'room_code': room_code,
            'players': [{
                'user_id': p['user_id'],
                'username': p['username'],
                'display_name': p.get('display_name', p['username']),
                'avatar': p.get('avatar', ''),
                'level': p.get('level', 1),
                'rank': p.get('rank', 'Beginner'),
                'is_ready': p.get('is_ready', False),
                'connected': p.get('connected', False),
            } for p in room['players']],
            'status': room['status'],
            'challenge_type': room['challenge_type'],
        }
    })


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

    if any(p['user_id'] == request.user.id for p in room['players']):
        # Reset finished rooms for replay (HTTP fallback for page reloads)
        if room['status'] == 'finished':
            room['status'] = 'waiting'
            room['challenge_type'] = room.get('challenge_type', 'typing')
            room['custom_settings'] = room.get('custom_settings')
            room.pop('challenge', None)
            for p in room['players']:
                p['is_ready'] = False
            cache.set(f'room_{room_code}', room)
        return JsonResponse({
            'room_code': room_code,
            'room': {
                'room_code': room_code,
                'players': [{
                    'user_id': p['user_id'],
                    'username': p['username'],
                    'display_name': p.get('display_name', p['username']),
                    'avatar': p.get('avatar', ''),
                    'level': p.get('level', 1),
                    'rank': p.get('rank', 'Beginner'),
                    'is_ready': p.get('is_ready', False),
                    'connected': p.get('connected', False),
                } for p in room['players']],
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

    return JsonResponse({
        'room_code': room_code,
        'room': {
            'room_code': room_code,
            'players': [{
                'user_id': p['user_id'],
                'username': p['username'],
                'display_name': p.get('display_name', p['username']),
                'avatar': p.get('avatar', ''),
                'level': p.get('level', 1),
                'rank': p.get('rank', 'Beginner'),
                'is_ready': p.get('is_ready', False),
                'connected': p.get('connected', False),
            } for p in room['players']],
            'status': room['status'],
            'challenge_type': room['challenge_type'],
            'custom_settings': room.get('custom_settings'),
        }
    })


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

    is_member = any(p['user_id'] == request.user.id for p in room['players'])
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


@login_required
def multiplayer_chat_poll(request):
    room_code = request.GET.get('room_code', '').upper().strip()
    after = int(request.GET.get('after', 0))
    if not room_code:
        return JsonResponse({'error': 'room_code required'}, status=400)

    key = f'chat_msgs_{room_code}'
    msgs = cache.get(key) or []
    new_msgs = [m for m in msgs if m['id'] > after]
    return JsonResponse({'messages': new_msgs})


@login_required
def multiplayer_room_state(request, room_code):
    room_code = room_code.upper().strip()
    room = cache.get(f'room_{room_code}')
    if not room:
        return JsonResponse({'error': 'Room not found'}, status=404)

    return JsonResponse({
        'room_code': room_code,
        'players': [{
            'user_id': p['user_id'],
            'username': p['username'],
            'display_name': p.get('display_name', p['username']),
            'avatar': p.get('avatar', ''),
            'level': p.get('level', 1),
            'rank': p.get('rank', 'Beginner'),
            'is_ready': p.get('is_ready', False),
            'connected': p.get('connected', False),
        } for p in room['players']],
        'status': room['status'],
        'challenge_type': room['challenge_type'],
        'winner_id': room.get('winner_id'),
        'winner_username': room.get('winner_username', ''),
    })

