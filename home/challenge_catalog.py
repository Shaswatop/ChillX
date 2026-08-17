"""
Challenge catalog for the AI challenge generator.

Holds the verified game/fitness/quiz data and the helper functions that
pick and build challenge templates.
"""

import os
import re


# Programiz online compilers — one per programming language. Coding
# challenges open the compiler for the language named in the title so the
# user can write/run their code in a browser instead of a local editor.
PROGRAMIZ_URLS = {
    "python":      "https://www.programiz.com/python-programming/online-compiler/",
    "javascript":  "https://www.programiz.com/javascript/online-compiler/",
    "typescript":  "https://www.programiz.com/typescript/online-compiler/",
    "java":        "https://www.programiz.com/java-programming/online-compiler/",
    "c":           "https://www.programiz.com/c-programming/online-compiler/",
    "cpp":         "https://www.programiz.com/cpp-programming/online-compiler/",
    "csharp":      "https://www.programiz.com/csharp-programming/online-compiler/",
    "html":        "https://www.programiz.com/html/online-compiler/",
    "css":         "https://www.programiz.com/html/online-compiler/",
    "sql":         "https://www.programiz.com/sql/online-compiler/",
    "go":          "https://www.programiz.com/golang/online-compiler/",
    "rust":        "https://www.programiz.com/rust/online-compiler/",
    "kotlin":      "https://www.programiz.com/kotlin-programming/online-compiler/",
    "php":         "https://www.programiz.com/php/online-compiler/",
    "swift":       "https://www.programiz.com/swift/online-compiler/",
    "ruby":        "https://www.programiz.com/ruby/online-compiler/",
    "scala":       "https://www.programiz.com/scala/online-compiler/",
    "dart":        "https://www.programiz.com/dart/online-compiler/",
    "r":           "https://www.programiz.com/r/online-compiler/",
}


# Figures out which programming language a coding challenge uses from the
# title/description. Returns a PROGRAMIZ_URLS key. Order matters: longer and
# more specific matches (c#, c++, javascript, typescript) come first so the
# single-letter and multi-language regexes never steal their match.
def detect_programiz_language(title, description=""):
    t = ((title or "") + " " + (description or "")).lower()

    def has(pattern):
        return re.search(pattern, t) is not None

    if has(r"javascript|node\.js|nodejs|ecmascript"):
        return "javascript"
    if has(r"typescript"):
        return "typescript"
    if has(r"c#|csharp|c sharp"):
        return "csharp"
    if has(r"c\+\+|cpp|c plus plus"):
        return "cpp"
    if has(r"python|python3|python 3"):
        return "python"
    if has(r"\bjava\b"):
        return "java"
    if has(r"golang|go lang|\bgo\b"):
        return "go"
    if has(r"\brust\b"):
        return "rust"
    if has(r"kotlin"):
        return "kotlin"
    if has(r"\bphp\b"):
        return "php"
    if has(r"\bswift\b"):
        return "swift"
    if has(r"\bruby\b"):
        return "ruby"
    if has(r"\bscala\b"):
        return "scala"
    if has(r"\bdart\b"):
        return "dart"
    if has(r"\bsql\b"):
        return "sql"
    if has(r"html|css"):
        return "html"
    if has(r"\bc\b|c language|c program"):
        return "c"
    if has(r"\br\b|r language"):
        return "r"
    return "python"


# In-app games (verified routes in home/urls.py)
# Pattern: /games/<game>/?target=<value>&time=<seconds>

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


# Figures out which exercise a fitness challenge is about from the title.
# If removed, fitness challenges won't get a matching exercise/mode.
# Edit the keyword list inside if a new exercise is added.
def detect_fitness_exercise(text):
    if not text:
        return None, "reps"
    t = text.lower()
    # Candidates with their key. Earliest match in the text wins.
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


# Builds the url for an in-app game with its target params attached.
# If removed, no game links get generated at all.
# Change the query string format here if needed.
def build_game_link(game_key, **params):
    game = IN_APP_GAMES.get(game_key)
    if not game:
        return ""
    url = game["url"]
    if params:
        parts = []
        for k, v in params.items():
            if v is not None:
                parts.append(f"{k}={v}")
        if parts:
            url = url + "?" + "&".join(parts)
    return url


# Offline categories that don't need a game link.
OFFLINE_CATEGORIES = {
    "coding", "art", "fitness", "quiz",
}


# Verified Poki game slugs — each one was confirmed to resolve (HTTP 200)
# on poki.com/en/g/<slug>. The AI frequently invents poki:<name> keys for
# games that don't exist on Poki, and blindly building a URL from that name
# produced 404s for the player. NEVER build a poki link for a slug that is
# not in this set.
POKI_SLUGS = {
    "2048", "age-of-war", "angry-birds", "basketball-master",
    "basketball-stars", "bottle-flip", "bubble-shooter", "chess",
    "crazy-cars", "cut-the-rope", "drive-mad", "ducklife", "ducklife-2",
    "ducklife-4", "ducklife-5", "fireboy-and-watergirl", "football-legends",
    "friday-night-funkin", "fruit-ninja", "geometry-dash", "gun-mayhem-2",
    "iron-snout", "learn-to-fly-3", "love-balls", "merge-cakes",
    "minecraft-classic", "monkey-mart", "moto-x3m", "mr-bullet", "paper-io",
    "paper-io-2", "parking-fury-3d", "penalty-shooters-2", "red-ball-4",
    "retro-bowl", "rooftop-snipers", "run-3", "shell-shockers", "slope",
    "smash-karts", "stack", "stickman-hook", "subway-surfers", "tag",
    "temple-of-boom", "temple-run", "temple-run-2", "tetris",
    "traffic-mania", "tunnel-rush", "worlds-hardest-game",
}

# Title/description keyword -> verified poki slug. Lets fix_challenge_link
# route a challenge whose title names a real Poki game even when the AI's
# game_key was wrong (or pointed at a non-existent slug).
POKI_TITLE_PHRASES = [
    ("bubble shooter", "bubble-shooter"),
    ("fruit ninja", "fruit-ninja"),
    ("subway surf", "subway-surfers"),
    ("temple run", "temple-run-2"),
    ("mr bullet", "mr-bullet"),
    ("iron snout", "iron-snout"),
    ("drive mad", "drive-mad"),
    ("merge cake", "merge-cakes"),
    ("moto x3m", "moto-x3m"),
    ("crazy car", "crazy-cars"),
    ("paper io", "paper-io-2"),
    ("tunnel rush", "tunnel-rush"),
    ("basketball star", "basketball-stars"),
    ("stickman hook", "stickman-hook"),
    ("penalty shooters", "penalty-shooters-2"),
    ("2048", "2048"),
    ("tetris", "tetris"),
    ("smash kart", "smash-karts"),
    ("geometry dash", "geometry-dash"),
    ("monkey mart", "monkey-mart"),
    ("retro bowl", "retro-bowl"),
    ("minecraft", "minecraft-classic"),
    ("friday night funkin", "friday-night-funkin"),
    ("shell shockers", "shell-shockers"),
    ("run 3", "run-3"),
    ("slope", "slope"),
    ("rooftop snipers", "rooftop-snipers"),
    ("stack", "stack"),
    ("red ball", "red-ball-4"),
    ("ducklife", "ducklife"),
    ("traffic mania", "traffic-mania"),
    ("gun mayhem", "gun-mayhem-2"),
    ("learn to fly", "learn-to-fly-3"),
    ("love balls", "love-balls"),
    ("cut the rope", "cut-the-rope"),
    ("bottle flip", "bottle-flip"),
    ("angry birds", "angry-birds"),
    ("football legends", "football-legends"),
    ("age of war", "age-of-war"),
    ("parking fury", "parking-fury-3d"),
    ("worlds hardest game", "worlds-hardest-game"),
    ("temple of boom", "temple-of-boom"),
    ("fireboy and watergirl", "fireboy-and-watergirl"),
    ("knife hit", "knife-hit"),
    ("chess", "chess"),
]


def find_poki_slug(name, title="", description=""):
    """Returns a verified poki slug for an AI name (or title text), or None.

    Checks, in order:
      1. the exact slug derived from the AI's poki:<name> key
      2. the title/description for a known game phrase
    Returns None when nothing verified matches, so callers never build a
    link that 404s.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    if slug in POKI_SLUGS:
        return slug
    text = f"{title or ''} {description or ''}".lower()
    for phrase, verified in POKI_TITLE_PHRASES:
        if phrase in text:
            return verified
    return None


# Scans the title/description for keywords to figure out the game.
# If removed, game detection stops and links fall back to nothing.
# Add new game keywords to the game_phrases list inside.
def detect_game_key(title, description="", category=""):
    text = (title or "") + " " + (description or "") + " " + (category or "")
    text = text.lower()

    # Each game has matching phrases. Order matters: in-app games first,
    # then poki games get appended after.
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
            "vex", "reach level", "platformer",
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

    # Search for the earliest phrase match
    best = None
    best_pos = 10**9
    for game_key, phrases in game_phrases:
        for phrase in phrases:
            pos = text.find(phrase)
            if pos >= 0 and pos < best_pos:
                best = game_key
                best_pos = pos

    return best


# The big one. Fixes the link and game_key on a generated challenge.
# If removed, every generated challenge loses its working link.
# Called from challenge_gen.py after the AI creates a challenge.
def fix_challenge_link(cd):
    cat = (cd.get("category") or "").lower().strip()
    title = cd.get("title") or ""
    desc = cd.get("description") or ""
    level = cd.get("_level", 1)

    explicit_gk = (cd.get("game_key") or "").strip().lower()

    # Coding challenges ALWAYS open the Programiz online compiler for the
    # language named in the title — this overrides any web:/poki: key/link
    # the AI produced. Third-party lesson sites (Codecademy, Codewars, ...)
    # require accounts and can't be verified, so every coding challenge
    # routes here.
    if cat == "coding":
        lang = detect_programiz_language(title, desc)
        cd["link"] = PROGRAMIZ_URLS.get(lang, PROGRAMIZ_URLS["python"])
        cd["game_key"] = "coding:programiz"
        cd["proof_type"] = "text"
        return cd

    # External web game — keep its real link so the Start button opens the
    # game site in the browser.
    if explicit_gk.startswith("poki:"):
        # Only build the poki.com URL when the slug is VERIFIED to exist on
        # Poki. The AI invents game names all the time (super_mario_bros,
        # chesscom, tetr.io, knife_hit ...) and those pages 404. If nothing
        # verifies, fall through to in-app detection so the challenge still
        # gets a working link.
        name = explicit_gk.split(":", 1)[1]
        slug = find_poki_slug(name, title, desc)
        if slug:
            cd["link"] = f"https://poki.com/en/g/{slug}"
            cd["game_key"] = f"poki:{slug.replace('-', '_')}"
            cd["proof_type"] = "image"
            return cd
        # Not a verified poki game — try the in-app catalog below.
        explicit_gk = ""

    if explicit_gk.startswith("web:"):
        if not cd.get("link"):
            cd["link"] = ""
            cd["proof_type"] = "image"
        else:
            cd["proof_type"] = "image"
        return cd

    if explicit_gk in IN_APP_GAMES:
        game_key = explicit_gk
    else:
        detected = detect_game_key(title, desc, cat)
        if detected and detected in IN_APP_GAMES:
            game_key = detected
        else:
            game_key = None

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

    # No specific game found — check if the category is offline
    cat_norm = cat.replace(" ", "")
    offline_words = (
        "code", "art", "design", "draw", "paint",
        "fitness", "gym", "workout", "exercise", "sport", "pushup",
        "music", "song", "instrument", "audio",
        "writ", "story", "journal", "content", "blog", "poem",
        "quiz", "trivia", "riddle", "gk",
    )
    is_offline = False
    for c in OFFLINE_CATEGORIES:
        if cat_norm.startswith(c):
            is_offline = True
            break
    if not is_offline:
        for x in offline_words:
            if x in cat:
                is_offline = True
                break
    if is_offline:
        # Art challenges get an online drawing tool link
        if cat == "art":
            cd["link"] = "https://kleki.com/"
            cd["game_key"] = "art:kleki"
        # Route fitness challenges to the in-app Fitness Studio
        elif cat in ("fitness", "workout", "exercise"):
            ex_key, ex_mode = detect_fitness_exercise(f"{title} {desc}")
            if ex_key:
                # Grab a target number from the title if present
                m = re.search(r'\b(\d+)\b', title)
                # Per-mode minimums: time=15s, reps=5, distance=0.5
                mode_floors = {"time": 15, "reps": 5, "distance": 0.5}
                default_targets = {"time": 30, "reps": 20, "distance": 1.0}
                if m:
                    if ex_mode == "distance":
                        target_val = float(m.group(1))
                    else:
                        target_val = int(m.group(1))
                    floor = mode_floors.get(ex_mode, 5)
                    if target_val < floor:
                        target_val = floor
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
            cd["link"] = ""
            cd["game_key"] = ""
        return cd

    # Gaming challenge with no game link found — the AI should have
    # provided a web: link, so leave it empty instead of inventing one.
    cd["link"] = ""
    cd["game_key"] = ""
    return cd


# Returns the target value a game should use for the user's level.
# If removed, in-app challenges have no scaled target.
# Tweak the level thresholds here to change difficulty.
def scale_target(game_key, level):
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
        # Default to pushups; fix_challenge_link refines from the title
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
# Local (no-AI) challenge generator
#
# The site must work with ZERO API keys configured — a user should be
# able to open the app and get a full daily batch of challenges right
# away. When every AI provider is missing/failing, this builds a batch
# from the verified in-app catalog + confirmed Poki slugs + Programiz
# compilers, then feeds it through fix_challenge_link/validate_challenge
# exactly like AI output, so every challenge gets a working link and a
# verifiable target.
# ─────────────────────────────────────────────────────────────────────

# Local challenge templates per category. Each entry is
# (title, description). fix_challenge_link fills in the link, game_key,
# scaled target and a proper description if one is missing, so these can
# stay short. Titles rotate per day so the batch isn't identical every day.
LOCAL_TEMPLATES = {
    "typing": [
        ("Reach the typing target on Monkeytype", ""),
        ("Beat the WPM target in a typing test", ""),
        ("Type the given passage and hit the WPM goal", ""),
    ],
    "reaction": [
        ("Beat the reaction time target", ""),
        ("React faster than the target in the reaction test", ""),
        ("Hit the reaction speed goal", ""),
    ],
    "cps": [
        ("Hit the CPS target in the click speed test", ""),
        ("Reach the clicks-per-second goal", ""),
        ("Beat the click speed target in the given time", ""),
    ],
    "aim3d": [
        ("Reach the score target in the 3D Aim Trainer", ""),
        ("Hit the aim score goal in 30 seconds", ""),
        ("Beat the target score in the 3D aim game", ""),
    ],
    "memory": [
        ("Reach the target level in Memory Match", ""),
        ("Clear the memory card levels to the goal", ""),
        ("Hit the memory match level target", ""),
    ],
    "tictactoe": [
        ("Win a game of Tic Tac Toe against the AI", ""),
        ("Beat the AI at Tic Tac Toe", ""),
    ],
    "runner": [
        ("Reach the score target in the Super Mario Runner", ""),
        ("Run the distance and hit the points goal", ""),
        ("Beat the runner score target without dying", ""),
    ],
    "fitness": [
        ("Do the target reps in the Fitness Studio", ""),
        ("Complete the fitness workout target", ""),
        ("Hit the exercise goal in the Fitness Studio", ""),
    ],
    "quiz": [
        ("Score the target on the AI Quiz", ""),
        ("Get the quiz score goal", ""),
        ("Beat the AI quiz target", ""),
    ],
    "coding": [
        ("Write a Python function that reverses a string", "Write it in the Python online compiler and run it to confirm."),
        ("Write a JavaScript function that sums an array", "Write it in the JavaScript online compiler and run it."),
        ("Write a C++ program that prints the Fibonacci series", "Write it in the C++ online compiler and run it."),
        ("Write a Python program that checks if a number is prime", "Write it in the Python online compiler and run it."),
        ("Write a Java program that prints Hello World", "Write it in the Java online compiler and run it."),
    ],
    "gaming": [
        ("Score 1000 points in Geometry Dash", "Play the verified Poki version and screenshot your score.", "poki:geometry_dash"),
        ("Play a round of Subway Surfers", "Play the verified Poki version and screenshot your run.", "poki:subway_surfers"),
        ("Score 2000 points in Tetris", "Play the verified Poki version and screenshot your score.", "poki:tetris"),
        ("Play a match of Basketball Stars", "Play the verified Poki version and screenshot the result.", "poki:basketball_stars"),
        ("Play a round of Temple Run 2", "Play the verified Poki version and screenshot your run.", "poki:temple_run_2"),
    ],
    "art": [
        ("Draw a sunset landscape in the online art tool", "Use the online drawing tool and screenshot your artwork."),
        ("Draw your favorite character in the art tool", "Use the online drawing tool and screenshot your artwork."),
        ("Create a neon-style digital painting", "Use the online drawing tool and screenshot your artwork."),
    ],
}


# Maps a category to the in-app game_key it maps to (None = handled by
# fix_challenge_link through the title/category instead).
LOCAL_CATEGORY_GAME = {
    "typing": "typing",
    "reaction": "reaction",
    "cps": "cps",
    "aim3d": "aim3d",
    "memory": "memory",
    "tictactoe": "tictactoe",
    "runner": "runner",
    "fitness": "fitness",
    "quiz": "quiz",
    "gaming": None,
    "coding": None,
    "art": None,
}


# Builds a full daily batch without any AI calls.
# If removed, the site needs an AI key to generate challenges at all.
# Used as the last-resort fallback in ai_service.generate_challenges.
def local_generate_challenges(categories, difficulty="medium", count=4, history=None, level=1, user=None):
    from datetime import date
    if not categories:
        categories = ["typing", "reaction", "cps", "aim3d", "memory", "quiz", "fitness", "gaming", "coding", "art"]
    if history is None:
        history = []
    seen_titles = set(history or [])
    # Rotate the template index by day so back-to-back days differ.
    day = date.today().toordinal()
    out = []
    for i, cat in enumerate(categories):
        if len(out) >= count:
            break
        cat = (cat or "").lower().strip()
        templates = LOCAL_TEMPLATES.get(cat)
        if not templates:
            continue
        # Pick a template, rotating by day + category index; skip repeats
        # already in the user's history when there's a fresh alternative.
        for offset in range(len(templates)):
            tpl = templates[(day + i + offset) % len(templates)]
            if tpl[0] not in seen_titles or offset == len(templates) - 1:
                break
        title = tpl[0]
        desc = tpl[1] if len(tpl) > 1 else ""
        explicit_gk = tpl[2] if len(tpl) > 2 else ""
        cd = {
            "title": title,
            "description": desc,
            "category": cat,
            "game_key": explicit_gk or LOCAL_CATEGORY_GAME.get(cat) or "",
            "proof_type": "text",
            "xp_reward": 50,
            "coin_reward": 10,
            "objective": "",
            "metric": "",
            "target": None,
            "unit": "",
            "estimated_duration": "",
            "special_condition": "",
            "_level": level,
        }
        cd = fix_challenge_link(cd)
        out.append(cd)
        seen_titles.add(title)
    return out

