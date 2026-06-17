"""
Challenge Catalog — verified training data with working links.

This is the "training set" for our AI challenge generator. Each entry has
been hand-verified to have:
  - A real, working link (in-app game, poki.com, or external tool)
  - A specific, measurable target that scales with user level
  - A proof_type matching the challenge
  - Sensible XP/coin rewards for its difficulty

The AI uses this catalog as few-shot examples. If AI generation fails, the
catalog itself is used as a high-quality fallback.
"""

from typing import Optional
import os


# ─────────────────────────────────────────────────────────────────────
# In-app games (verified routes in home/urls.py)
# Pattern: /games/<game>/?target=<value>&time=<seconds>
# ─────────────────────────────────────────────────────────────────────

IN_APP_GAMES = {
    "typing": {
        "url": "https://monkeytype.com",
        "label": "Monkeytype (typing test)",
        "icon": "fas fa-keyboard",
        "scoring": "wpm",       # higher is better
        "external": True,
    },
    "reaction": {
        "url": "/games/reaction/",
        "label": "Reaction Test",
        "icon": "fas fa-bolt",
        "scoring": "ms_lower",  # lower ms is better (max allowed)
    },
    "cps": {
        "url": "/games/cps/",
        "label": "Click Speed",
        "icon": "fas fa-mouse-pointer",
        "scoring": "cps",       # higher is better
    },
    "aim3d": {
        "url": "/games/aim3d/",
        "label": "3D Aim Trainer",
        "icon": "fas fa-bullseye",
        "scoring": "score",
    },
    "memory": {
        "url": "/games/memory/",
        "label": "Memory Match",
        "icon": "fas fa-brain",
        "scoring": "level",
    },
    "tictactoe": {
        "url": "/games/tictactoe/",
        "label": "Tic Tac Toe vs AI",
        "icon": "fas fa-th",
        "scoring": "wins",
    },
    "runner": {
        "url": "/games/runner/",
        "label": "Super Mario Runner",
        "icon": "fas fa-running",
        "scoring": "points",
    },
    "fitness": {
        "url": "/games/fitness/",
        "label": "Fitness Studio",
        "icon": "fas fa-dumbbell",
        "scoring": "mixed",
    },
    "quiz": {
        "url": "/games/quiz/",
        "label": "AI Quiz",
        "icon": "fas fa-question-circle",
        "scoring": "score",
    },
}


# Fitness exercises — exercise_key → (mode, default_target_by_level, unit)
FITNESS_EXERCISES = {
    "pushups":           {"mode": "reps",     "label": "Pushups",      "icon": "fa-hand-fist",         "pace": 1800},
    "squats":            {"mode": "reps",     "label": "Squats",       "icon": "fa-person",            "pace": 2000},
    "burpees":           {"mode": "reps",     "label": "Burpees",      "icon": "fa-person-running",    "pace": 2500},
    "lunges":            {"mode": "reps",     "label": "Lunges",       "icon": "fa-person-walking",    "pace": 2000},
    "jumping_jacks":     {"mode": "reps",     "label": "Jumping Jacks","icon": "fa-person",            "pace": 1200},
    "sit_ups":           {"mode": "reps",     "label": "Sit-ups",      "icon": "fa-bed",               "pace": 2000},
    "high_knees":        {"mode": "reps",     "label": "High Knees",   "icon": "fa-person-running",    "pace": 1000},
    "mountain_climbers": {"mode": "reps",     "label": "Mountain Climbers", "icon": "fa-mountain",     "pace": 800},
    "calf_raises":       {"mode": "reps",     "label": "Calf Raises",  "icon": "fa-person",            "pace": 1500},
    "plank":             {"mode": "time",     "label": "Plank",        "icon": "fa-bars",              "pace": 0},
    "wall_sit":          {"mode": "time",     "label": "Wall Sit",     "icon": "fa-person",            "pace": 0},
    "running":           {"mode": "distance", "label": "Running",      "icon": "fa-person-running",    "pace": 0},
}


def detect_fitness_exercise(text: str) -> tuple[str | None, str]:
    """Detect fitness exercise from text. Returns (exercise_key, mode) or (None, 'reps').

    Uses POSITION-based detection (earliest match wins) so the first exercise
    mentioned in the title overrides later mentions in the description.
    """
    if not text:
        return None, "reps"
    t = text.lower()
    # All candidates, with their key. POSITION-BASED match — find the earliest.
    candidates = [
        ("mountain climber", "mountain_climbers"),
        ("mountain climb", "mountain_climbers"),
        ("jumping jack", "jumping_jacks"),
        ("jumping jacks", "jumping_jacks"),
        ("high knee", "high_knees"),
        ("sit up", "sit_ups"),
        ("sit-up", "sit_ups"),
        ("crunch", "sit_ups"),
        ("calf raise", "calf_raises"),
        ("wall sit", "wall_sit"),
        ("burpee", "burpees"),
        ("pushup", "pushups"),
        ("push up", "pushups"),
        ("push-up", "pushups"),
        ("squat", "squats"),
        ("lunge", "lunges"),
        ("plank", "plank"),
        ("jogging", "running"),
        ("jog", "running"),
        ("run", "running"),
    ]
    best_key = None
    best_pos = 10**9
    for needle, key in candidates:
        pos = t.find(needle)
        if pos >= 0 and pos < best_pos:
            best_key = key
            best_pos = pos
    if best_key:
        return best_key, FITNESS_EXERCISES[best_key]["mode"]
    return None, "reps"


def build_game_link(game_key: str, **params) -> str:
    """Build a working in-app game link with target params."""
    game = IN_APP_GAMES.get(game_key)
    if not game:
        return ""
    url = game["url"]
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        if qs:
            url = f"{url}?{qs}"
    return url


# Map category names (as the AI may produce them) to canonical in-app game keys
CATEGORY_TO_GAME = {
    "typing": "typing", "type": "typing", "wpm": "typing", "keybr": "typing",
    "reaction": "reaction", "reflex": "reaction", "reaction time": "reaction",
    "cps": "cps", "click": "cps", "click speed": "cps", "clicking": "cps",
    "aim3d": "aim3d", "3d aim": "aim3d", "fps": "aim3d", "3d aim trainer": "aim3d",
    "aim": "aim3d", "aim trainer": "aim3d", "tile frenzy": "aim3d", "2d aim": "aim3d", "shooting": "aim3d",
    "memory": "memory", "memory match": "memory", "brain": "memory",
    "tictactoe": "tictactoe", "tic tac toe": "tictactoe", "xo": "tictactoe",
    "runner": "runner", "endless runner": "runner", "running": "runner",
    "fitness": "fitness", "workout": "fitness", "exercise": "fitness", "gym": "fitness",
    "quiz": "quiz", "trivia": "quiz", "gk": "quiz", "general knowledge": "quiz",
}


def expected_game_for_category(category: str) -> str | None:
    """Map a category string to the expected in-app game key, or None if no in-app game fits."""
    if not category:
        return None
    cat = category.strip().lower()
    if cat in CATEGORY_TO_GAME:
        return CATEGORY_TO_GAME[cat]
    for k, v in CATEGORY_TO_GAME.items():
        if k in cat or cat in k:
            return v
    return None


OFFLINE_CATEGORIES = {
    "coding", "art", "fitness", "quiz",
}


def detect_game_key(title: str, description: str = "", category: str = "") -> str | None:
    """
    Detect the in-app game this challenge belongs to from its text.

    Returns the canonical game_key (typing, reaction, cps, aim3d, memory,
    tictactoe, runner) or None if no in-app game is referenced.

    Detection order is strict and deterministic — the FIRST match wins.
    """
    text = f"{title or ''} {description or ''} {category or ''}".lower()

    # Each game has a set of phrases. Whichever game's phrases appear first
    # in the text wins. Order matters: in-app games first, then poki games.
    game_phrases = [
        ("tictactoe", [
            "tic tac toe", "tic-tac-toe", "tictactoe", "noughts and crosses",
            "x and o", "xs and os", "play xo", "win a tic", "x's and o's",
        ]),
        ("typing", [
            "typing test", "typing speed", "wpm", "words per minute",
            "keyboard test", "type 20", "type 30", "type 40", "type 50",
            "monkeytype", "keybr", "typing.com", "typeracer", "type fast",
        ]),
        ("reaction", [
            "reaction time", "reaction test", "reaction speed",
            "human benchmark reaction", "milliseconds", "average 250ms",
            "average 200ms", "average 300ms", "average 350ms", "average 400ms",
            "faster than", "reflex test", "react quickly", "test your reflexes",
            "click when", "wait for green", "wait for the color",
        ]),
        ("cps", [
            "cps test", "click speed", "clicks per second", "click test",
            "kohi click", "jitter click", "butter click", "clicks in",
        ]),
        ("aim3d", [
            "3d aim", "fps aim", "aim trainer", "tile frenzy",
            "shooting range", "target practice", "shoot targets",
            "aim practice", "first person aim", "3d shooter", "fps game",
            "aim training", "practice your aim",
        ]),
        ("memory", [
            "memory match", "memory game", "memory card", "card match",
            "brain game", "match the cards", "concentration game",
            "remember the", "match pairs", "pairs game",
        ]),
        ("runner", [
            "endless runner", "running game", "dash game", "side scroller",
            "jump and run", "avoid obstacles", "run as far", "run for",
            "distance run", "running distance", "dinosaur game",
        ]),
        ("fitness", [
            "fitness studio", "in the fitness", "fitness tool", "workout tool",
            "fitness app", "fitness game", "follow the avatar", "chibi avatar",
            "fitness challenge", "in-app fitness", "fitness mode",
            "open the fitness", "use the fitness", "rep counter", "workout app",
        ]),
        ("quiz", [
            "ai quiz", "quiz game", "quiz challenge", "trivia quiz",
            "answer questions", "multiple choice quiz", "brain quiz",
        ]),
    ]

    # Append poki game detection — any popular poki game mentioned in text
    for pg in POKI_GAMES:
        pat = pg["title_pattern"].lower()
        # Use the poki key as a marker; the caller (fix_challenge_link) maps this to URL
        game_phrases.append((f"poki:{pg['key']}", [pat]))

    # Search for the earliest occurrence of any phrase in the text
    best = None
    best_pos = 10**9
    for game_key, phrases in game_phrases:
        for phrase in phrases:
            pos = text.find(phrase)
            if pos >= 0 and pos < best_pos:
                best = game_key
                best_pos = pos

    return best


def get_poki_game(poki_key: str):
    """Look up a poki game by key. Returns the dict or None."""
    for pg in POKI_GAMES:
        if pg["key"] == poki_key:
            return pg
    return None


def _poki_target_for_level(poki_game: dict, level: int):
    """Get (title, target_value, difficulty) for a poki game at user level."""
    for (lo, hi), entry in poki_game["targets_by_level"].items():
        if lo <= level <= hi:
            return entry
    # Default to easy if level out of range
    return poki_game["targets_by_level"].get((1, 10), (poki_game["title_pattern"], 1, "easy"))


def fix_challenge_link(cd: dict) -> dict:
    """
    Post-process a generated challenge dict to ensure the link and game_key
    are correct, strict, and deterministic.

    Rules (in order):
      1. If the AI provided a valid game_key (in-app OR poki), use it.
      2. Otherwise, detect the game from the title/description via keyword scan.
         The FIRST game keyword in the text wins — no hashing, no randomness.
      3. If a game_key can be determined, build the link from the catalog
         and save the game_key on the dict.
      4. If the category is offline (coding/art/fitness/etc.) and no game is
         mentioned, strip the link (user just needs the Join button).
      5. If the category is gaming and no specific game is mentioned in the
         text, deterministically pick a popular poki game (same title = same game).
    """
    import hashlib
    cat = (cd.get("category") or "").lower().strip()
    title = cd.get("title") or ""
    desc = cd.get("description") or ""
    level = cd.get("_level", 1)

    explicit_gk = (cd.get("game_key") or "").strip().lower()
    if explicit_gk in IN_APP_GAMES:
        game_key = explicit_gk
        poki_game = None
    elif explicit_gk.startswith("poki:"):
        game_key = explicit_gk
        poki_game = get_poki_game(explicit_gk.split(":", 1)[1])
    else:
        detected = detect_game_key(title, desc, cat)
        if detected and detected in IN_APP_GAMES:
            game_key = detected
            poki_game = None
        elif detected and detected.startswith("poki:"):
            game_key = detected
            poki_game = get_poki_game(detected.split(":", 1)[1])
        else:
            game_key = None
            poki_game = None

    # In-app game branch
    if game_key in IN_APP_GAMES:
        scaled = scale_target(game_key, level)
        # Fitness: refine exercise/mode/target from title/description
        if game_key == "fitness":
            ex_key, ex_mode = detect_fitness_exercise(f"{title} {desc}")
            if ex_key:
                scaled["exercise"] = ex_key
                scaled["mode"] = FITNESS_EXERCISES[ex_key]["mode"]
            else:
                scaled.setdefault("exercise", "pushups")
                scaled.setdefault("mode", "reps")
            cd["link"] = build_game_link(game_key, **scaled)
            cd["game_key"] = game_key
            cd["proof_type"] = "text"  # in-app tool auto-verifies
            if not desc:
                ex_label = FITNESS_EXERCISES.get(scaled["exercise"], {}).get("label", "exercise")
                t = scaled.get("target", "?")
                if scaled["mode"] == "reps":
                    cd["description"] = f"Do {t} {ex_label.lower()} and tap +1 for each rep. The chibi avatar will follow along."
                elif scaled["mode"] == "time":
                    cd["description"] = f"Hold {ex_label.lower()} for {t} seconds. Click Done when finished."
                else:
                    cd["description"] = f"{ex_label} for the target distance. Timer counts up — click Done and log your distance."
            return cd
        cd["link"] = build_game_link(game_key, **scaled)
        cd["game_key"] = game_key
        cd["proof_type"] = "text" if game_key == "tictactoe" else "image"
        if not desc:
            g = IN_APP_GAMES[game_key]
            t = scaled.get("target", "?")
            unit = {
                "typing": f"score at least {t} WPM",
                "reaction": f"average {t}ms or faster",
                "cps": f"score at least {t} CPS in {scaled.get('time', 10)} seconds",
                "aim3d": f"score at least {t} points in {scaled.get('time', 30)} seconds",
                "memory": f"reach level {t}",
                "tictactoe": "win a game against the AI",
                "runner": f"score at least {t} points",
                "quiz": f"score at least {t}/10",
            }.get(game_key, "complete the challenge")
            cd["description"] = f"Play {g['label']} and {unit}. Screenshot your result."
        return cd

    # Poki game branch (detected by name or via AI explicit game_key)
    if poki_game:
        title_pattern, target_val, difficulty = _poki_target_for_level(poki_game, level)
        cd["link"] = poki_game["url"]
        cd["game_key"] = f"poki:{poki_game['key']}"
        cd["proof_type"] = "image"
        if not desc:
            cd["description"] = f"{title_pattern}: complete the in-game target and screenshot the result."
        return cd

    # No specific game found — check if category is offline
    cat_norm = cat.replace(" ", "")
    is_offline = any(cat_norm.startswith(c) for c in OFFLINE_CATEGORIES) or any(
        x in cat for x in (
            "code", "art", "design", "draw", "paint",
            "fitness", "gym", "workout", "exercise", "sport", "pushup",
            "music", "song", "instrument", "audio",
            "writ", "story", "journal", "content", "blog", "poem",
            "quiz", "trivia", "riddle", "gk",
        )
    )
    if is_offline:
        # Art challenges get an online drawing tool link
        if cat == "art":
            cd["link"] = "https://kleki.com/"
            cd["game_key"] = "art:kleki"
        # Fitness challenges with a detected exercise get routed to in-app Fitness Studio
        elif cat in ("fitness", "workout", "exercise"):
            ex_key, ex_mode = detect_fitness_exercise(f"{title} {desc}")
            if ex_key:
                # Try to extract target number from title (e.g. "Do 20 pushups" → 20)
                import re as _re
                m = _re.search(r'\b(\d+)\b', title)
                # Per-mode minimum: time=15s, reps=5, distance=0.5km
                mode_floors = {"time": 15, "reps": 5, "distance": 0.5}
                default_targets = {"time": 30, "reps": 20, "distance": 1.0}
                if m:
                    target_val = int(m.group(1)) if ex_mode != "distance" else float(m.group(1))
                    target_val = max(target_val, mode_floors.get(ex_mode, 5))
                else:
                    target_val = default_targets.get(ex_mode, 20)
                cd["link"] = build_game_link("fitness", target=target_val, exercise=ex_key, mode=ex_mode)
                cd["game_key"] = "fitness"
                cd["proof_type"] = "text"  # in-app tool auto-verifies
                if not desc:
                    ex_label = FITNESS_EXERCISES.get(ex_key, {}).get("label", "exercise")
                    t = target_val
                    if ex_mode == "reps":
                        cd["description"] = f"Do {t} {ex_label.lower()} and tap +1 for each rep. The chibi avatar will follow along."
                    elif ex_mode == "time":
                        cd["description"] = f"Hold {ex_label.lower()} for {t} seconds. Click Done when finished."
                    else:
                        cd["description"] = f"{ex_label} for the target distance. Timer counts up — click Done and log your distance."
                return cd
            # No specific exercise detected — fall back to pushups default
            scaled = scale_target("fitness", level)
            cd["link"] = build_game_link("fitness", **scaled)
            cd["game_key"] = "fitness"
            cd["proof_type"] = "text"
            return cd
        elif cat in ("quiz", "trivia"):
            # Route quiz challenges to the in-app AI Quiz game
            scaled = scale_target("quiz", level)
            cd["link"] = build_game_link("quiz", **scaled)
            cd["game_key"] = "quiz"
            cd["proof_type"] = "image"
            t = scaled.get("target", 5)
            if not desc:
                cd["description"] = f"Open the AI Quiz, pick any topic, and score at least {t}/10. Screenshot your final score."
            return cd
        else:
            if cat == "coding":
                # Open VS Code at a dedicated coding projects folder
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                projects_dir = os.path.join(base_dir, "coding_challenges")
                os.makedirs(projects_dir, exist_ok=True)
                cd["link"] = "vscode://file/" + projects_dir.replace("\\", "/").replace(" ", "%20")
                cd["game_key"] = "coding:vscode"
            else:
                cd["link"] = ""
                cd["game_key"] = ""
        return cd

    # Gaming category fallback: pick a popular poki game deterministically
    # based on the title/seed. Same title = same game, no randomness.
    is_gaming = any(x in cat for x in ("game", "gaming", "play", "poki", "subway", "temple", "moto", "stickman", "basket", "kart", "knife", "knife", "shoot"))
    if is_gaming and POKI_GAMES:
        seed = f"{title}|{desc}|{cat}|{level}"
        h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        chosen = POKI_GAMES[h % len(POKI_GAMES)]
        title_pattern, target_val, difficulty = _poki_target_for_level(chosen, level)
        cd["link"] = chosen["url"]
        cd["game_key"] = f"poki:{chosen['key']}"
        cd["proof_type"] = "image"
        if not desc:
            cd["description"] = f"Play {title_pattern} and complete the in-game target. Screenshot the result."
        return cd

    cd["link"] = ""
    cd["game_key"] = ""
    return cd


def scale_target(game_key: str, level: int) -> dict:
    """Return scaled target params for a given in-app game and user level."""
    if game_key == "typing":
        if level < 5:    target = 15
        elif level < 15: target = 25
        elif level < 30: target = 35
        else:            target = 50
        return {"target": target}
    if game_key == "reaction":
        if level < 5:    target = 350
        elif level < 15: target = 280
        elif level < 30: target = 220
        else:            target = 180
        return {"target": target}
    if game_key == "cps":
        if level < 5:    target, time = 4, 10
        elif level < 15: target, time = 5, 10
        elif level < 30: target, time = 7, 10
        else:            target, time = 9, 5
        return {"target": target, "time": time}
    if game_key == "aim3d":
        if level < 5:    target = 500
        elif level < 15: target = 1000
        elif level < 30: target = 2000
        else:            target = 3000
        return {"target": target, "time": 30}
    if game_key == "memory":
        if level < 5:    target = 2
        elif level < 15: target = 4
        elif level < 30: target = 6
        else:            target = 10
        return {"target": target}
    if game_key == "tictactoe":
        return {"target": "Beat_the_AI"}
    if game_key == "runner":
        if level < 5:    target = 5
        elif level < 15: target = 11
        else:            target = 21
        return {"target": target}
    if game_key == "fitness":
        # Default to pushups for auto-gen; AI/fix_challenge_link refines exercise from title
        if level < 5:    target = 10
        elif level < 15: target = 20
        elif level < 30: target = 30
        else:            target = 50
        return {"target": target, "exercise": "pushups", "mode": "reps"}
    if game_key == "quiz":
        if level < 5:    target = 5
        elif level < 15: target = 7
        elif level < 30: target = 8
        else:            target = 10
        return {"target": target}
    return {}


# ─────────────────────────────────────────────────────────────────────
# Verified poki.com games (browser, free, no login)
# ─────────────────────────────────────────────────────────────────────

POKI_GAMES = [
    {
        "key": "subway_surfers",
        "title_pattern": "Subway Surfers",
        "url": "https://poki.com/en/g/subway-surfers",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 200 in Subway Surfers", 200, "easy"),
            (11, 30): ("Score 800 in Subway Surfers", 800, "medium"),
            (31, 60): ("Score 2,000 in Subway Surfers", 2000, "hard"),
        },
    },
    {
        "key": "temple_run_2",
        "title_pattern": "Temple Run 2",
        "url": "https://poki.com/en/g/temple-run-2",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Survive 1 minute in Temple Run 2", 60, "easy"),
            (11, 30): ("Score 2,000 in Temple Run 2", 2000, "medium"),
            (31, 60): ("Score 10,000 in Temple Run 2", 10000, "hard"),
        },
    },
    {
        "key": "moto_x3m",
        "title_pattern": "Moto X3M",
        "url": "https://poki.com/en/g/moto-x3m",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Complete 5 levels in Moto X3M", 5, "easy"),
            (11, 30): ("Complete 12 levels in Moto X3M", 12, "medium"),
            (31, 60): ("Complete all Moto X3M levels", 22, "hard"),
        },
    },
    {
        "key": "stickman_hook",
        "title_pattern": "Stickman Hook",
        "url": "https://poki.com/en/g/stickman-hook",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 50 in Stickman Hook", 50, "easy"),
            (11, 30): ("Score 200 in Stickman Hook", 200, "medium"),
            (31, 60): ("Score 500 in Stickman Hook", 500, "hard"),
        },
    },
    {
        "key": "basketball_stars",
        "title_pattern": "Basketball Stars",
        "url": "https://poki.com/en/g/basketball-stars",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 10 points in Basketball Stars", 10, "easy"),
            (11, 30): ("Score 25 points in Basketball Stars", 25, "medium"),
            (31, 60): ("Score 50 points in Basketball Stars", 50, "hard"),
        },
    },
    {
        "key": "rooftop_snipers",
        "title_pattern": "Rooftop Snipers",
        "url": "https://poki.com/en/g/rooftop-snipers",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 3 points in Rooftop Snipers", 3, "easy"),
            (11, 30): ("Score 10 points in Rooftop Snipers", 10, "medium"),
            (31, 60): ("Score 25 points in Rooftop Snipers", 25, "hard"),
        },
    },
    {
        "key": "knife_hit",
        "title_pattern": "Mr Bullet",
        "url": "https://poki.com/en/g/mr-bullet",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Clear 5 levels in Mr Bullet", 5, "easy"),
            (11, 30): ("Clear 12 levels in Mr Bullet", 12, "medium"),
            (31, 60): ("Clear 25 levels in Mr Bullet", 25, "hard"),
        },
    },
    {
        "key": "smash_karts",
        "title_pattern": "Smash Karts",
        "url": "https://poki.com/en/g/smash-karts",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Finish a Smash Karts race in top 3", 3, "easy"),
            (11, 30): ("Win 3 Smash Karts races", 3, "medium"),
            (31, 60): ("Win 10 Smash Karts races", 10, "hard"),
        },
    },
    {
        "key": "paper_io_2",
        "title_pattern": "Paper.io 2",
        "url": "https://poki.com/en/g/paper-io-2",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Capture 30% of the map in Paper.io 2", 30, "easy"),
            (11, 30): ("Win a Paper.io 2 match", 1, "medium"),
            (31, 60): ("Win 5 Paper.io 2 matches", 5, "hard"),
        },
    },
    {
        "key": "raft_wars",
        "title_pattern": "Raft Wars",
        "url": "https://poki.com/en/g/raft-wars",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Complete level 5 in Raft Wars", 5, "easy"),
            (11, 30): ("Complete level 12 in Raft Wars", 12, "medium"),
            (31, 60): ("Complete all Raft Wars levels", 18, "hard"),
        },
    },
    {
        "key": "8_ball_pool",
        "title_pattern": "Pool Club",
        "url": "https://poki.com/en/g/pool-club",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Pot 5 balls in Pool Club", 5, "easy"),
            (11, 30): ("Win 3 Pool Club matches", 3, "medium"),
            (31, 60): ("Win 10 Pool Club matches", 10, "hard"),
        },
    },
    {
        "key": "bubble_shooter",
        "title_pattern": "Bubble Shooter",
        "url": "https://poki.com/en/g/bubble-shooter",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 1,000 in Bubble Shooter", 1000, "easy"),
            (11, 30): ("Score 5,000 in Bubble Shooter", 5000, "medium"),
            (31, 60): ("Score 20,000 in Bubble Shooter", 20000, "hard"),
        },
    },
    {
        "key": "blumgi_ball",
        "title_pattern": "Blumgi Ball",
        "url": "https://poki.com/en/g/blumgi-ball",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 5 goals in Blumgi Ball", 5, "easy"),
            (11, 30): ("Score 15 goals in Blumgi Ball", 15, "medium"),
            (31, 60): ("Score 40 goals in Blumgi Ball", 40, "hard"),
        },
    },
    {
        "key": "house_of_hazards",
        "title_pattern": "House of Hazards",
        "url": "https://poki.com/en/g/house-of-hazards",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Win 1 round in House of Hazards", 1, "easy"),
            (11, 30): ("Win 5 rounds in House of Hazards", 5, "medium"),
            (31, 60): ("Win 15 rounds in House of Hazards", 15, "hard"),
        },
    },
    {
        "key": "tag",
        "title_pattern": "Tag",
        "url": "https://poki.com/en/g/tag",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Survive 60 seconds in Tag", 60, "easy"),
            (11, 30): ("Survive 3 minutes in Tag", 180, "medium"),
            (31, 60): ("Win 5 matches in Tag", 5, "hard"),
        },
    },
    {
        "key": "bearsus",
        "title_pattern": "BearSUS",
        "url": "https://poki.com/en/g/bearsus",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Complete 3 tasks in BearSUS", 3, "easy"),
            (11, 30): ("Win 1 match in BearSUS", 1, "medium"),
            (31, 60): ("Win 5 matches in BearSUS", 5, "hard"),
        },
    },
    {
        "key": "soccer_skills",
        "title_pattern": "Soccer Skills",
        "url": "https://poki.com/en/g/soccer-skills-euro-cup",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 3 goals in Soccer Skills", 3, "easy"),
            (11, 30): ("Score 8 goals in Soccer Skills", 8, "medium"),
            (31, 60): ("Score 20 goals in Soccer Skills", 20, "hard"),
        },
    },
    {
        "key": "crazy_cars",
        "title_pattern": "Crazy Cars",
        "url": "https://poki.com/en/g/crazy-cars",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Survive 60 seconds in Crazy Cars", 60, "easy"),
            (11, 30): ("Survive 3 minutes in Crazy Cars", 180, "medium"),
            (31, 60): ("Score 10,000 in Crazy Cars", 10000, "hard"),
        },
    },
    {
        "key": "go_kart_go_ultra",
        "title_pattern": "Go Kart Go Ultra",
        "url": "https://poki.com/en/g/go-kart-go-ultra",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Win 1 race in Go Kart Go Ultra", 1, "easy"),
            (11, 30): ("Win 5 races in Go Kart Go Ultra", 5, "medium"),
            (31, 60): ("Win 15 races in Go Kart Go Ultra", 15, "hard"),
        },
    },
    {
        "key": "stickman_fighting",
        "title_pattern": "Stickman Fighter: Epic Battle",
        "url": "https://poki.com/en/g/stickman-fighter-epic-battle",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Win 1 fight in Stickman Fighter", 1, "easy"),
            (11, 30): ("Win 5 fights in Stickman Fighter", 5, "medium"),
            (31, 60): ("Win 15 fights in Stickman Fighter", 15, "hard"),
        },
    },
    {
        "key": "tunnel_rush",
        "title_pattern": "Tunnel Rush",
        "url": "https://poki.com/en/g/tunnel-rush",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Survive 30 seconds in Tunnel Rush", 30, "easy"),
            (11, 30): ("Survive 90 seconds in Tunnel Rush", 90, "medium"),
            (31, 60): ("Survive 3 minutes in Tunnel Rush", 180, "hard"),
        },
    },
    {
        "key": "rocket_soccer_derby",
        "title_pattern": "Rocket Soccer Derby",
        "url": "https://poki.com/en/g/rocket-soccer-derby",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 3 goals in Rocket Soccer Derby", 3, "easy"),
            (11, 30): ("Win 1 match in Rocket Soccer Derby", 1, "medium"),
            (31, 60): ("Win 5 matches in Rocket Soccer Derby", 5, "hard"),
        },
    },
    {
        "key": "parking_fury",
        "title_pattern": "Parking Fury",
        "url": "https://poki.com/en/g/parking-fury",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Park 5 cars in Parking Fury", 5, "easy"),
            (11, 30): ("Park 15 cars in Parking Fury", 15, "medium"),
            (31, 60): ("Complete all levels in Parking Fury", 25, "hard"),
        },
    },
    {
        "key": "rally_point",
        "title_pattern": "Rally Point",
        "url": "https://poki.com/en/g/rally-point",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Finish 1 race in Rally Point", 1, "easy"),
            (11, 30): ("Finish 5 races in Rally Point", 5, "medium"),
            (31, 60): ("Win 10 races in Rally Point", 10, "hard"),
        },
    },
    {
        "key": "dunk_shot",
        "title_pattern": "Penalty Shooters 2",
        "url": "https://poki.com/en/g/penalty-shooters-2",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 5 goals in Penalty Shooters 2", 5, "easy"),
            (11, 30): ("Score 15 goals in Penalty Shooters 2", 15, "medium"),
            (31, 60): ("Win 5 matches in Penalty Shooters 2", 5, "hard"),
        },
    },
    {
        "key": "iron_snout",
        "title_pattern": "Iron Snout",
        "url": "https://poki.com/en/g/iron-snout",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Survive 60 seconds in Iron Snout", 60, "easy"),
            (11, 30): ("Score 50 in Iron Snout", 50, "medium"),
            (31, 60): ("Score 150 in Iron Snout", 150, "hard"),
        },
    },
    {
        "key": "moto_x3m_spooky",
        "title_pattern": "Moto X3M Spooky Land",
        "url": "https://poki.com/en/g/moto-x3m-spooky-land",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Complete 5 levels in Moto X3M Spooky", 5, "easy"),
            (11, 30): ("Complete 12 levels in Moto X3M Spooky", 12, "medium"),
            (31, 60): ("Complete all Moto X3M Spooky levels", 22, "hard"),
        },
    },
    {
        "key": "super_mario_bros",
        "title_pattern": "Super Mario Bros",
        "url": "https://poki.com/en/g/super-mario-bros",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Complete world 1-4 in Super Mario Bros", 4, "easy"),
            (11, 30): ("Complete world 4-4 in Super Mario Bros", 16, "medium"),
            (31, 60): ("Complete world 8-4 in Super Mario Bros", 32, "hard"),
        },
    },
    {
        "key": "fireboy_and_watergirl",
        "title_pattern": "Fireboy and Watergirl",
        "url": "https://poki.com/en/g/fireboy-and-watergirl-forest-temple",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Complete 5 levels in Fireboy and Watergirl", 5, "easy"),
            (11, 30): ("Complete 15 levels in Fireboy and Watergirl", 15, "medium"),
            (31, 60): ("Complete all levels in Fireboy and Watergirl", 35, "hard"),
        },
    },
    {
        "key": "stacker",
        "title_pattern": "Stacker",
        "url": "https://poki.com/en/g/stacker",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Stack 20 blocks in Stacker", 20, "easy"),
            (11, 30): ("Stack 50 blocks in Stacker", 50, "medium"),
            (31, 60): ("Stack 100 blocks in Stacker", 100, "hard"),
        },
    },
    {
        "key": "cookie_clicker",
        "title_pattern": "Cookie Clicker",
        "url": "https://poki.com/en/g/cookie-clicker",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Bake 1,000 cookies in Cookie Clicker", 1000, "easy"),
            (11, 30): ("Bake 10,000 cookies in Cookie Clicker", 10000, "medium"),
            (31, 60): ("Bake 100,000 cookies in Cookie Clicker", 100000, "hard"),
        },
    },
    {
        "key": "merge_rounds",
        "title_pattern": "Merge Round Racers",
        "url": "https://poki.com/en/g/merge-round-racers",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Reach car level 5 in Merge Round Racers", 5, "easy"),
            (11, 30): ("Reach car level 10 in Merge Round Racers", 10, "medium"),
            (31, 60): ("Reach car level 20 in Merge Round Racers", 20, "hard"),
        },
    },
    {
        "key": "merge_cakes",
        "title_pattern": "Merge Cakes",
        "url": "https://poki.com/en/g/merge-cakes",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 500 in Merge Cakes", 500, "easy"),
            (11, 30): ("Score 2,500 in Merge Cakes", 2500, "medium"),
            (31, 60): ("Score 10,000 in Merge Cakes", 10000, "hard"),
        },
    },
    {
        "key": "tetris",
        "title_pattern": "Tetris",
        "url": "https://poki.com/en/g/tetris",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 5,000 in Tetris", 5000, "easy"),
            (11, 30): ("Score 25,000 in Tetris", 25000, "medium"),
            (31, 60): ("Score 100,000 in Tetris", 100000, "hard"),
        },
    },
    {
        "key": "2048",
        "title_pattern": "2048",
        "url": "https://poki.com/en/g/2048",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Reach 256 in 2048", 256, "easy"),
            (11, 30): ("Reach 1024 in 2048", 1024, "medium"),
            (31, 60): ("Reach 2048 in 2048", 2048, "hard"),
        },
    },
    {
        "key": "solitaire",
        "title_pattern": "Solitaire",
        "url": "https://poki.com/en/g/solitaire",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Win 1 Solitaire game", 1, "easy"),
            (11, 30): ("Win 5 Solitaire games", 5, "medium"),
            (31, 60): ("Win 20 Solitaire games", 20, "hard"),
        },
    },
    {
        "key": "monkey_mart",
        "title_pattern": "Monkey Mart",
        "url": "https://poki.com/en/g/monkey-mart",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Earn 500 coins in Monkey Mart", 500, "easy"),
            (11, 30): ("Earn 2,500 coins in Monkey Mart", 2500, "medium"),
            (31, 60): ("Earn 10,000 coins in Monkey Mart", 10000, "hard"),
        },
    },
    {
        "key": "drive_mad",
        "title_pattern": "Drive Mad",
        "url": "https://poki.com/en/g/drive-mad",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Complete 5 levels in Drive Mad", 5, "easy"),
            (11, 30): ("Complete 12 levels in Drive Mad", 12, "medium"),
            (31, 60): ("Complete all Drive Mad levels", 30, "hard"),
        },
    },
    {
        "key": "retro_bowl",
        "title_pattern": "Retro Bowl",
        "url": "https://poki.com/en/g/retro-bowl",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Win 1 season game in Retro Bowl", 1, "easy"),
            (11, 30): ("Win 5 season games in Retro Bowl", 5, "medium"),
            (31, 60): ("Win the Retro Bowl championship", 17, "hard"),
        },
    },
    {
        "key": "drift_boss",
        "title_pattern": "Drift Boss",
        "url": "https://poki.com/en/g/drift-boss",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 100 in Drift Boss", 100, "easy"),
            (11, 30): ("Score 500 in Drift Boss", 500, "medium"),
            (31, 60): ("Score 2,000 in Drift Boss", 2000, "hard"),
        },
    },
    {
        "key": "temple_of_boom",
        "title_pattern": "Temple of Boom",
        "url": "https://poki.com/en/g/temple-of-boom",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Win 1 round in Temple of Boom", 1, "easy"),
            (11, 30): ("Win 5 rounds in Temple of Boom", 5, "medium"),
            (31, 60): ("Win 20 rounds in Temple of Boom", 20, "hard"),
        },
    },
    {
        "key": "fruit_ninja",
        "title_pattern": "Fruit Ninja",
        "url": "https://poki.com/en/g/fruit-ninja",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 50 in Fruit Ninja", 50, "easy"),
            (11, 30): ("Score 200 in Fruit Ninja", 200, "medium"),
            (31, 60): ("Score 500 in Fruit Ninja", 500, "hard"),
        },
    },
    {
        "key": "mr_bullet",
        "title_pattern": "Mr Bullet",
        "url": "https://poki.com/en/g/mr-bullet",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Clear 5 levels in Mr Bullet", 5, "easy"),
            (11, 30): ("Clear 15 levels in Mr Bullet", 15, "medium"),
            (31, 60): ("Clear 30 levels in Mr Bullet", 30, "hard"),
        },
    },
    {
        "key": "penalty_shooters_2",
        "title_pattern": "Penalty Shooters 2",
        "url": "https://poki.com/en/g/penalty-shooters-2",
        "category": "gaming",
        "proof_type": "image",
        "targets_by_level": {
            (1, 10):  ("Score 5 goals in Penalty Shooters 2", 5, "easy"),
            (11, 30): ("Score 15 goals in Penalty Shooters 2", 15, "medium"),
            (31, 60): ("Win 5 matches in Penalty Shooters 2", 5, "hard"),
        },
    },
]


# ─────────────────────────────────────────────────────────────────────
# Verified offline / tool-based challenges (no URL needed, description only)
# ─────────────────────────────────────────────────────────────────────

FITNESS_CHALLENGES = {
    (1, 10):  [
        ("Do 10 pushups in one set", "Do 10 consecutive pushups with proper form. Drop and give me 10!", "text", 30, 6, "easy"),
        ("Hold a plank for 30 seconds", "Hold a plank position for 30 seconds without breaking form. Core strength!", "text", 30, 6, "easy"),
        ("Do 20 squats", "Perform 20 bodyweight squats with good form. Feel the burn!", "text", 30, 6, "easy"),
        ("Walk 2,000 steps", "Get moving! Walk at least 2,000 steps. Anywhere counts.", "text", 35, 7, "easy"),
    ],
    (11, 30): [
        ("Do 30 pushups in one set", "Do 30 consecutive pushups without stopping. Proper form counts!", "text", 60, 12, "medium"),
        ("Hold a plank for 1 min 30 sec", "Hold a plank for a full 90 seconds. No sagging!", "text", 60, 12, "medium"),
        ("Do 50 squats", "50 bodyweight squats in one go. Keep your back straight!", "text", 50, 10, "medium"),
        ("Run 1 km without stopping", "Run or jog 1 kilometer continuously. Pace yourself!", "text", 80, 16, "medium"),
        ("Do 20 burpees in one set", "20 burpees as fast as you can with good form.", "text", 70, 14, "medium"),
    ],
    (31, 60): [
        ("Do 50 pushups in one set", "50 consecutive pushups is the goal. No breaks!", "text", 100, 20, "hard"),
        ("Hold a plank for 3 minutes", "3-minute plank hold. Mental toughness wins.", "text", 120, 24, "hard"),
        ("Run 5 km without stopping", "Run 5 kilometers without walking. Time yourself!", "text", 200, 40, "hard"),
        ("Do 50 burpees in one set", "50 burpees in a single set. Full body exhaustion!", "text", 150, 30, "hard"),
    ],
}


CODING_CHALLENGES = {
    (1, 10):  [
        ("Build a tip calculator with HTML/CSS/JS", "Build a working tip calculator web app that takes a bill amount and tip percentage and shows the result. Share the code or a screenshot.", "text", 60, 12, "easy"),
        ("Create a todo list app", "Make a simple todo list with HTML, CSS, and JavaScript where you can add and remove tasks. Show your work.", "text", 70, 14, "easy"),
        ("Make a random quote generator", "Build a page that shows a new random motivational quote when you click a button. Use any tech you like.", "text", 50, 10, "easy"),
    ],
    (11, 30): [
        ("Build a weather app with a real API", "Use OpenWeatherMap or similar to build a weather app that shows current weather for any city. Share the GitHub repo or live URL.", "text", 120, 24, "medium"),
        ("Make a snake game in JavaScript", "Recreate the classic Snake game playable in the browser. Use canvas or DOM.", "text", 150, 30, "medium"),
        ("Create a REST API with Python Flask", "Build a simple REST API with at least 3 endpoints (GET, POST, DELETE). Document with a README.", "text", 130, 26, "medium"),
        ("Solve 5 problems on LeetCode (Easy)", "Pick 5 easy problems, solve them, and share your solution or profile screenshot.", "text", 100, 20, "medium"),
    ],
    (31, 60): [
        ("Build a full-stack web app", "Create a full-stack app with frontend, backend, and database. Examples: blog, expense tracker, chat app. Deploy it somewhere and share the URL.", "text", 300, 60, "hard"),
        ("Contribute to an open source repo", "Find a GitHub repo with 'good first issue' tags, fix or improve something, and submit a PR. Share the PR link.", "text", 350, 70, "hard"),
        ("Build a real-time chat with WebSockets", "Create a chat app using WebSockets (Socket.io, Django Channels, or similar) where multiple users can chat in real time.", "text", 400, 80, "hard"),
    ],
}


ART_CHALLENGES = {
    (1, 10):  [
        ("Draw a self-portrait", "Spend 20 minutes drawing your self-portrait. Any medium. Take a photo of the result.", "image", 60, 12, "easy"),
        ("Sketch your favorite animal", "Draw your favorite animal in 15 minutes. Show the final sketch.", "image", 50, 10, "easy"),
        ("Color a digital page", "Use any coloring app or print a coloring page and finish it. Screenshot the result.", "image", 40, 8, "easy"),
    ],
    (11, 30): [
        ("Draw a fantasy character", "Design and draw an original fantasy character with a backstory. Spend at least 45 minutes.", "image", 120, 24, "medium"),
        ("Create a pixel art scene", "Make a 64x64 or 128x128 pixel art scene (landscape, character, etc.) using a tool like Aseprite or Pixilart.", "image", 130, 26, "medium"),
        ("Paint a landscape", "Paint a landscape scene (digital or physical) in an hour. Show the final result.", "image", 110, 22, "medium"),
    ],
    (31, 60): [
        ("Create a comic strip", "Draw a 4-panel comic strip with a story. Spend at least 2 hours. Share the final comic.", "image", 250, 50, "hard"),
        ("Design a video game character", "Design a complete character with concept art, turnaround, and color variants. Show the full sheet.", "image", 300, 60, "hard"),
    ],
}


QUIZ_CHALLENGES = {
    (1, 10):  [
        ("World's Biggest Countries Quiz", "Name the top 10 biggest countries by area. Write down all 10 from memory. One try, no cheating!", "text", 40, 8, "easy"),
        ("Solve 5 Riddles", "Find 5 riddles online or from memory and write down the answers. Bonus if you stump a friend!", "text", 35, 7, "easy"),
        ("AI Full Forms Quiz", "What do AI, NLP, ML, CNN, and GPT stand for? Write down all 5 without looking them up.", "text", 30, 6, "easy"),
        ("Guess the Nepali Gau Khane Katha", "Name 5 Nepali folktales (Gau Khane Katha) you remember from childhood. Write their main moral or lesson.", "text", 45, 9, "easy"),
    ],
    (11, 30): [
        ("World Capitals Challenge", "Write down the capitals of 15 randomly chosen countries. Score at least 10/15 to pass.", "text", 80, 16, "medium"),
        ("Tech Acronyms Marathon", "Decode 10 tech acronyms (HTTP, API, JSON, SQL, CSS, HTML, DNS, RAM, SSD, URL). Write the full form of each.", "text", 60, 12, "medium"),
        ("Nepali Samanya Gyan Quiz", "Answer 10 general knowledge questions about Nepal — geography, history, culture, and famous figures. Write your answers.", "text", 70, 14, "medium"),
        ("Riddle Gaun — 7 Riddles in 7 Minutes", "Solve 7 riddles in 7 minutes. Write each riddle's answer before the timer runs out. No googling!", "text", 90, 18, "medium"),
        ("AI Concepts Explained Simply", "Explain 5 AI/ML concepts (Neural Network, Training, Overfitting, LLM, Token) in simple terms as if teaching a 12-year-old.", "text", 85, 17, "medium"),
    ],
    (31, 60): [
        ("The Ultimate World Quiz", "Answer 20 world GK questions across geography, history, science, and pop culture. Score 16/20 to pass.", "text", 150, 30, "hard"),
        ("Full Forms Gauntlet", "Write the full forms of 25 tech, medical, and general acronyms. One shot, no retries.", "text", 130, 26, "hard"),
        ("Nepal Expert Challenge", "Answer 20 detailed questions about Nepal — from ancient kingdoms to modern politics, from Himalayan peaks to cultural festivals.", "text", 180, 36, "hard"),
        ("AI & Future Tech Deep Quiz", "Answer 15 questions about AI ethics, future tech, robotics, and emerging technologies. Write detailed answers with reasoning.", "text", 200, 40, "hard"),
        ("Create Your Own Quiz", "Design a 10-question quiz on any topic you love. Include answers. Share it with the community.", "text", 120, 24, "hard"),
    ],
}


# ─────────────────────────────────────────────────────────────────────
# Lookup helpers
# ─────────────────────────────────────────────────────────────────────

def _level_band(level: int):
    """Return the (min, max) band tuple for a given level."""
    if level <= 10:  return (1, 10)
    if level <= 30:  return (11, 30)
    return (31, 60)


def get_inapp_challenge(game_key: str, level: int) -> Optional[dict]:
    """Build a challenge dict for an in-app game, scaled to level."""
    if game_key not in IN_APP_GAMES:
        return None
    game = IN_APP_GAMES[game_key]
    params = scale_target(game_key, level)
    link = build_game_link(game_key, **params)
    band = _level_band(level)
    target = params.get("target")
    time = params.get("time")

    # Title patterns per game
    if game_key == "typing":
        title = f"Type {target} WPM"
        desc = f"Play the Typing Test and score at least {target} WPM. Screenshot your result."
        proof = "image"
    elif game_key == "reaction":
        title = f"React in under {target}ms"
        desc = f"Take the Reaction Test and average under {target}ms across 5 attempts. Screenshot your best time."
        proof = "image"
    elif game_key == "cps":
        title = f"Hit {target} CPS in {time}s"
        desc = f"Open the Click Speed Test and score at least {target} clicks per second in {time} seconds. Screenshot your result."
        proof = "image"
    elif game_key == "aim3d":
        title = f"Score {target} in 3D Aim Trainer"
        desc = f"Play the 3D Aim Trainer (Tile Frenzy) for {time} seconds and score at least {target} points. Screenshot your result."
        proof = "image"
    elif game_key == "memory":
        title = f"Reach level {target} in Memory Match"
        desc = f"Play Memory Match and reach at least level {target}. Screenshot your high score."
        proof = "image"
    elif game_key == "tictactoe":
        title = f"Win a game of Tic Tac Toe"
        desc = f"Play Tic Tac Toe vs the AI and win at least one game. Screenshot your win."
        proof = "image"
    elif game_key == "runner":
        title = f"Run {target}m in Endless Runner"
        desc = f"Play the Endless Runner and survive at least {target} meters. Screenshot your score."
        proof = "image"
    elif game_key == "quiz":
        title = f"Score {target}/10 in AI Quiz"
        desc = f"Open the AI Quiz, pick any topic, and score at least {target} out of 10 questions. Screenshot your final score."
        proof = "image"
    else:
        return None

    # Difficulty scaling
    if level <= 10:  diff, xp, coin = "easy", 30, 6
    elif level <= 30: diff, xp, coin = "medium", 60, 12
    else:             diff, xp, coin = "hard", 100, 20

    return {
        "title": title,
        "description": desc,
        "category": game_key,  # typing/cps/reaction/aim3d/memory/tictactoe/runner — matches the user's selected interest
        "proof_type": proof,
        "xp_reward": xp,
        "coin_reward": coin,
        "is_long": False,
        "link": link,
        "difficulty": diff,
        "_band": band,
        "_game_key": game_key,
    }


def get_poki_challenge(poki_key: str, level: int) -> Optional[dict]:
    """Build a challenge dict for a poki.com game."""
    game = next((g for g in POKI_GAMES if g["key"] == poki_key), None)
    if not game:
        return None
    band = _level_band(level)
    target_entry = None
    for lvl_band, entry in game["targets_by_level"].items():
        if lvl_band[0] <= level <= lvl_band[1]:
            target_entry = entry
            break
    if not target_entry:
        return None
    title, target, diff = target_entry
    if diff == "easy":   xp, coin = 40, 8
    elif diff == "medium": xp, coin = 80, 16
    else:                xp, coin = 150, 30
    return {
        "title": title,
        "description": f"Play {game['title_pattern']} on Poki and {title.lower().replace(game['title_pattern'].lower(), '').strip()}. Screenshot your final score.",
        "category": "gaming",
        "proof_type": "image",
        "xp_reward": xp,
        "coin_reward": coin,
        "is_long": False,
        "link": game["url"],
        "difficulty": diff,
        "_band": band,
        "_game_key": poki_key,
    }


def get_offline_challenge(category: str, level: int) -> Optional[dict]:
    """Build a challenge dict for an offline/tool-based category."""
    catalog = {
        "fitness": FITNESS_CHALLENGES,
        "coding": CODING_CHALLENGES,
        "art": ART_CHALLENGES,
        "quiz": QUIZ_CHALLENGES,
    }.get(category)
    if not catalog:
        return None
    band = _level_band(level)
    options = catalog.get(band, [])
    if not options:
        return None
    import random
    title, desc, proof, xp, coin, diff = random.choice(options)
    return {
        "title": title,
        "description": desc,
        "category": category,
        "proof_type": proof,
        "xp_reward": xp,
        "coin_reward": coin,
        "is_long": False,
        "link": "",
        "difficulty": diff,
        "_band": band,
    }


# ─────────────────────────────────────────────────────────────────────
# Few-shot examples for the AI prompt
# ─────────────────────────────────────────────────────────────────────

# Hand-crafted CREATIVE examples that teach the AI the "objective-based"
# challenge style. These are the gold standard — the AI should generate
# challenges with the same vibe, NOT "Score X in Y" templates.
CREATIVE_FEW_SHOT_EXAMPLES = [
    {
        "title": "Complete a word in Subway Surfers",
        "description": "Letters are scattered all over the tracks — grab them all and finish a word. Easy win, screenshot the moment it spells out.",
        "category": "gaming",
        "game_key": "poki:subway_surfers",
        "proof_type": "image",
        "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Hire your first employee in Monkey Mart",
        "description": "Time to stop running that mart solo. Stack up enough bananas and bring on your very first hire.",
        "category": "gaming",
        "game_key": "poki:monkey_mart",
        "proof_type": "image",
        "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Clear a 4-line Tetris",
        "description": "A real Tetris — four lines gone in one drop. The big one. Can you do it?",
        "category": "gaming",
        "game_key": "poki:tetris",
        "proof_type": "image",
        "xp_reward": 80, "coin_reward": 16,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Reach the 256 tile in 2048",
        "description": "256 is where the game starts getting real. Merge your way there — 128s aren't safe forever.",
        "category": "gaming",
        "game_key": "poki:2048",
        "proof_type": "image",
        "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Survive 1 minute in Tunnel Rush without hitting red",
        "description": "Eyes up, hands steady. One full minute in the tunnel without a single crash.",
        "category": "gaming",
        "game_key": "poki:tunnel_rush",
        "proof_type": "image",
        "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Make a 3-pointer in Basketball Stars",
        "description": "Step behind the line and let it fly. One 3-pointer is all you need — make it count.",
        "category": "gaming",
        "game_key": "poki:basketball_stars",
        "proof_type": "image",
        "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Get your first win in Smash Karts using a green shell",
        "description": "Hunt down your opponents with a green shell, cross the line first. If you're gonna win, win with style.",
        "category": "gaming",
        "game_key": "poki:smash_karts",
        "proof_type": "image",
        "xp_reward": 80, "coin_reward": 16,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Finish a level without crashing in Moto X3M",
        "description": "Easy does it — no flips, no ragdolls, no 'oops'. Just clean it and move on.",
        "category": "gaming",
        "game_key": "poki:moto_x3m",
        "proof_type": "image",
        "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "One-shot a level in Mr Bullet",
        "description": "Bullet economy. Solve the whole level without missing once. Minimum bullets, maximum smugness.",
        "category": "gaming",
        "game_key": "poki:mr_bullet",
        "proof_type": "image",
        "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Collect 200 coins in a single Temple Run 2 run",
        "description": "Coins scatter across the ancient ruins — grab 200 of them in one run without wiping out. Coin collection is the real Temple Run endgame.",
        "category": "gaming",
        "game_key": "poki:temple_run_2",
        "proof_type": "image",
        "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Capture 30% of the map in Paper.io 2",
        "description": "Claim a third of the arena in a single match. Bold moves, sharp turns, no regrets.",
        "category": "gaming",
        "game_key": "poki:paper_io_2",
        "proof_type": "image",
        "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Win your first match in Stickman Fighter",
        "description": "Stickman life: a hundred hits, one winner. Make sure it's you.",
        "category": "gaming",
        "game_key": "poki:stickman_fighter",
        "proof_type": "image",
        "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Bake your first 1,000 cookies in Cookie Clicker",
        "description": "Click click click. Bake 1,000 cookies — the original clicker milestone.",
        "category": "gaming",
        "game_key": "poki:cookie_clicker",
        "proof_type": "image",
        "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Hit 25 WPM with 90%+ accuracy in the Typing Test",
        "description": "25 WPM, 90% accuracy — no sloppy typos. Quality speed, not just speed.",
        "category": "typing",
        "game_key": "typing",
        "proof_type": "image",
        "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Get a sub-200ms reaction time",
        "description": "Sub-200ms. Five tries, one shot. Catch that screen-change the second it flips.",
        "category": "reaction",
        "game_key": "reaction",
        "proof_type": "image",
        "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Beat your CPS personal best by 10%",
        "description": "Three tries, one goal — smash your old CPS by 10%. Don't hold back.",
        "category": "cps",
        "game_key": "cps",
        "proof_type": "image",
        "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Reach level 5 in Memory Match without a single mistake",
        "description": "Perfect run. Level 5, zero mistakes. Every flip counts — eyes on the board.",
        "category": "gaming",
        "game_key": "memory",
        "proof_type": "image",
        "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Win a Tic Tac Toe match in under 6 moves",
        "description": "Crush the AI in 6 moves or fewer. A clean, surgical win.",
        "category": "gaming",
        "game_key": "tictactoe",
        "proof_type": "text",
        "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Write a 200-word short story that makes the reader laugh",
        "description": "200 words, one punchline. Make someone actually laugh — punchline lands on the last line.",
        "game_key": "",
        "proof_type": "text",
        "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Draw a hand from observation",
        "description": "Stare at your hand for a minute. Then draw it. Hands are the boss fight of figure drawing — this is real practice.",
        "category": "art",
        "game_key": "",
        "proof_type": "image",
        "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
]


# Offline-category few-shot examples (art, music, fitness, writing, coding)
# Teaches the AI that not every challenge is gaming.
OFFLINE_FEW_SHOT_EXAMPLES = [
    {
        "title": "Draw your morning coffee from observation",
        "description": "Look at your actual coffee mug right now. 30-second study, then draw it from memory. Real objects, real light, real life.",
        "category": "art", "game_key": "",
        "proof_type": "image", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Learn and play the first 4 bars of any song on guitar",
        "description": "YouTube a beginner guitar tutorial, learn 4 bars, record yourself playing them. First real chord progression is the gateway to every song you'll ever play.",
        "proof_type": "both", "xp_reward": 80, "coin_reward": 16,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "30 jumping jacks, 20 squats, 10 push-ups — 3 rounds",
        "description": "No equipment, no excuses. Three rounds of jumping jacks, squats, push-ups. 15 minutes, total body, real sweat. Screenshot your timer at the end.",
        "category": "fitness", "game_key": "",
        "proof_type": "image", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Write the worst opening sentence to a novel",
        "description": "It was a dark and stormy night... but make it YOURS. Write 3 opening sentences so bad they're good. Bonus points for clichés.",
        "proof_type": "text", "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Build a FizzBuzz script in Python from scratch",
        "description": "Open a code editor, write FizzBuzz from 1-100 without looking it up. If you Google it, you didn't really do it. Screenshot your working code.",
        "category": "coding", "game_key": "",
        "proof_type": "image", "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Sketch your hand in 5 different positions",
        "description": "Open hand, fist, peace sign, point, thumbs up. 5 sketches, 60 seconds each. Hands are the boss fight of figure drawing — this is the speed run.",
        "category": "art", "game_key": "",
        "proof_type": "image", "xp_reward": 100, "coin_reward": 20,
        "is_long": True, "link": "", "difficulty": "hard",
    },
    {
        "title": "Hold a plank for 90 seconds straight",
        "description": "Forearm plank, body straight, no sagging. 90 seconds is the wall most people hit — break through it. Screenshot your stopwatch.",
        "category": "fitness", "game_key": "",
        "proof_type": "image", "xp_reward": 80, "coin_reward": 16,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Write a 6-line poem where every line starts with the next letter of the alphabet",
        "description": "A, B, C, D, E, F — six lines, each starting with the next letter. Constraint is the creativity. Make it actually poetic, not random.",
        "proof_type": "text", "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Build a working calculator in HTML/CSS/JS",
        "description": "One HTML file, one CSS, one JS. Buttons 0-9, +, -, ×, ÷, =, C. No frameworks. Make it actually work. Screenshot the result.",
        "category": "coding", "game_key": "",
        "proof_type": "both", "xp_reward": 100, "coin_reward": 20,
        "is_long": True, "link": "", "difficulty": "hard",
    },
    {
        "title": "Hum your favorite song, then write down its chord progression",
        "description": "Even if you don't play an instrument. Listen, hum, identify the I-IV-V or vi-IV-I-V. Ear training for the win.",
        "proof_type": "text", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Draw your kitchen from memory without looking",
        "description": "30 seconds to look, then close your eyes and draw what you remember. The fridge, the sink, the window, the weird magnet. Real memory, real art.",
        "category": "art", "game_key": "",
        "proof_type": "image", "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Run in place for 5 minutes without stopping",
        "description": "Doesn't matter how slow. Knees up, arms pumping, no breaks. 5 minutes of cardio on the spot. Screenshot your timer.",
        "category": "fitness", "game_key": "",
        "proof_type": "image", "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Write a 6-line poem about the last thing that annoyed you",
        "description": "Real annoyance, real poem. 6 lines max, rhyme or not, your call. Sometimes the best writing comes from the most annoying moments.",
        "proof_type": "text", "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Plank for 60 seconds, perfect form",
        "description": "Forearms down, body straight, hips tucked. Hold for 60 seconds, no sagging, no piking. Screenshot the timer at the end.",
        "category": "fitness", "game_key": "",
        "proof_type": "image", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Sing the chorus of your favorite song from memory",
        "description": "No lyrics on screen, no auto-tune, just you. Pick a song you love, sing the chorus, record audio or video. Real voice, real feel.",
        "proof_type": "both", "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Write a function that reverses a string (any language)",
        "description": "No built-in reverse. Loop, slice, recursion, whatever. Test it on your own name. Screenshot the code and the output.",
        "category": "coding", "game_key": "",
        "proof_type": "image", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Paint a 1-inch square of your favorite color in 5 shades",
        "description": "Five tiny squares, same color, lightest to darkest. Trains your eye for value. Photograph them side by side.",
        "category": "art", "game_key": "",
        "proof_type": "image", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Build a CSS-only animated loading spinner",
        "description": "No JS, no images, no libraries. Pure CSS keyframes + a single div. Should spin forever. Screenshot the spinner and paste the CSS.",
        "category": "coding", "game_key": "",
        "proof_type": "image", "xp_reward": 80, "coin_reward": 16,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Solve the first 3 kata on Codewars (8 kyu)",
        "description": "Pick any 3 easy kata in any language you like. No copy-paste from the solutions tab. Screenshot your completed kata.",
        "category": "coding", "game_key": "",
        "proof_type": "image", "xp_reward": 70, "coin_reward": 14,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Sing the alphabet backwards without stopping",
        "description": "Z, Y, X... all the way to A. If you stumble, restart. Record yourself. The struggle is the point.",
        "proof_type": "both", "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "10-minute no-phone morning routine (real one)",
        "description": "Stretch + water + one page of a book + 30 sec of stillness. Real routine, not scroll. Screenshot the timer at the end.",
        "category": "fitness", "game_key": "",
        "proof_type": "image", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "Name the 7 wonders of the world from memory",
        "description": "No looking it up. New 7, old 7, your call. Write down all 7. If you get 5+ you're already ahead of most people.",
        "category": "quiz", "game_key": "",
        "proof_type": "text", "xp_reward": 40, "coin_reward": 8,
        "is_long": False, "link": "", "difficulty": "easy",
    },
    {
        "title": "Decode 10 tech acronyms in 2 minutes",
        "description": "HTTP, API, JSON, SQL, CSS, HTML, DNS, RAM, SSD, URL. Type the full form for each. 2 minutes on the clock. Go.",
        "category": "quiz", "game_key": "",
        "proof_type": "text", "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "", "difficulty": "medium",
    },
    {
        "title": "A Riddle a Day keeps the boredom away — solve 5",
        "description": "Find or remember 5 riddles. Write the answers. Classic ones, tricky ones, Nepali ones — anything goes. Stump your friends after.",
        "category": "quiz", "game_key": "",
        "proof_type": "text", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "", "difficulty": "easy",
    },
]


# In-app fitness few-shot examples — fitness challenges that use the in-app
# Fitness Studio tool. The AI should prefer these when the user has fitness in
# their preferences, instead of generating "do 20 pushups, screenshot" challenges.
IN_APP_FITNESS_EXAMPLES = [
    {
        "title": "Bang out 20 pushups in one set",
        "description": "Open the Fitness Studio and follow the chibi avatar. Tap +1 for each rep, match the avatar's pace. 20 reps, no breaks.",
        "category": "fitness", "game_key": "fitness",
        "proof_type": "text", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "/games/fitness/?exercise=pushups&target=20&mode=reps", "difficulty": "medium",
    },
    {
        "title": "Wall sit for 60 seconds, no break",
        "description": "Open the Fitness Studio on Wall Sit mode. Back against the wall, thighs parallel to floor. Hold for the full minute. The avatar holds the pose with you.",
        "category": "fitness", "game_key": "fitness",
        "proof_type": "text", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "/games/fitness/?exercise=wall_sit&target=60&mode=time", "difficulty": "medium",
    },
    {
        "title": "Plank for 90 seconds, perfect form",
        "description": "Forearm plank, body straight, no sagging. Open the Fitness Studio on Plank mode and hit 90 seconds. The timer counts up automatically.",
        "category": "fitness", "game_key": "fitness",
        "proof_type": "text", "xp_reward": 80, "coin_reward": 16,
        "is_long": False, "link": "/games/fitness/?exercise=plank&target=90&mode=time", "difficulty": "medium",
    },
    {
        "title": "30 jumping jacks in one go",
        "description": "Jumping jacks, follow the avatar's beat. Tap +1 each time your feet come back together. 30 reps, no breaks.",
        "category": "fitness", "game_key": "fitness",
        "proof_type": "text", "xp_reward": 30, "coin_reward": 6,
        "is_long": False, "link": "/games/fitness/?exercise=jumping_jacks&target=30&mode=reps", "difficulty": "easy",
    },
    {
        "title": "10 burpees, real form",
        "description": "Squat, plank, pushup, jump. Follow the avatar's 4-phase animation. Tap +1 at the top of each jump. 10 reps, full body.",
        "category": "fitness", "game_key": "fitness",
        "proof_type": "text", "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "/games/fitness/?exercise=burpees&target=10&mode=reps", "difficulty": "medium",
    },
    {
        "title": "20 lunges (10 each leg)",
        "description": "Step forward, drop back knee, drive up. Alternate legs. Follow the avatar. Tap +1 for each lunge. 20 total.",
        "category": "fitness", "game_key": "fitness",
        "proof_type": "text", "xp_reward": 50, "coin_reward": 10,
        "is_long": False, "link": "/games/fitness/?exercise=lunges&target=20&mode=reps", "difficulty": "medium",
    },
    {
        "title": "Squat 30 times in one set",
        "description": "Knees behind toes, hips back, chest up. Follow the chibi squat rhythm. Tap +1 each time you stand. 30 squats.",
        "category": "fitness", "game_key": "fitness",
        "proof_type": "text", "xp_reward": 60, "coin_reward": 12,
        "is_long": False, "link": "/games/fitness/?exercise=squats&target=30&mode=reps", "difficulty": "medium",
    },
    {
        "title": "Run 1 km, log your time",
        "description": "Outdoor run, jog, treadmill, or track. Open the Fitness Studio on Running mode, hit START, and log your km when you're back. Be honest.",
        "category": "fitness", "game_key": "fitness",
        "proof_type": "text", "xp_reward": 80, "coin_reward": 16,
        "is_long": False, "link": "/games/fitness/?exercise=running&target=1&mode=distance", "difficulty": "medium",
    },
]


def get_few_shot_examples(level: int = 5, user_prefs=None) -> list:
    """
    Return 4-6 creative objective-based example challenges to show the AI.
    Mixes gaming/poki examples with offline (art, music, fitness, writing, coding, quiz)
    examples so the AI doesn't default to gaming.

    If user_prefs is given, prioritizes offline examples whose category is
    in the user's preferences, so the AI sees relevant offline examples.
    """
    import random
    gaming_pool = list(CREATIVE_FEW_SHOT_EXAMPLES)
    offline_pool = list(OFFLINE_FEW_SHOT_EXAMPLES)
    in_app_fitness_pool = list(IN_APP_FITNESS_EXAMPLES)
    random.shuffle(gaming_pool)
    random.shuffle(offline_pool)
    random.shuffle(in_app_fitness_pool)

    # If user has fitness in prefs, prioritize in-app fitness examples
    # (these are higher quality than generic "screenshot your pushups" prompts)
    if user_prefs and 'fitness' in user_prefs:
        # Mix 1-2 in-app fitness + 2-3 other offline
        n_fitness = min(2, len(in_app_fitness_pool))
        in_app_fitness_pool = in_app_fitness_pool[:n_fitness]
        # Filter offline fitness out since we replaced it
        offline_pool = [e for e in offline_pool if e.get('category') != 'fitness']

    if user_prefs:
        # Surface offline examples that match user prefs
        matched = [e for e in offline_pool if e.get('category') in user_prefs]
        other = [e for e in offline_pool if e.get('category') not in user_prefs]
        offline_pool = matched + other

    # Pick 4 offline + 2 gaming so the AI always sees the offline pattern
    # (was 3+2, but the AI kept dropping one interest — 4 offline examples
    # weights the model's distribution toward offline categories)
    n = random.randint(5, 6)
    offline_count = min(4, len(offline_pool))
    gaming_count = max(1, n - offline_count)
    picked = offline_pool[:offline_count] + gaming_pool[:gaming_count] + in_app_fitness_pool
    random.shuffle(picked)
    return picked


def format_examples_for_prompt(level: int = 5, user_prefs=None) -> str:
    """Format few-shot examples as a JSON string for the AI prompt."""
    import json
    examples = get_few_shot_examples(level, user_prefs=user_prefs)
    return json.dumps(examples, indent=2)
