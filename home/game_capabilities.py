"""
Game capability map — the authoritative definition of what each built-in
game can genuinely measure and enforce.

Used to validate and clamp AI-generated challenge objectives so the AI can
never invent mechanics a game doesn't support. This is game-integrity data,
NOT a hardcoded challenge list. The AI remains the creative engine; this
file is the backend authority on bounds.

Bounds are conservative guard rails. The real per-level target scaling lives
in challenge_catalog.scale_target(); this file only sanity-checks the AI's
metric/target against what the actual game can produce.
"""

import math


# metric -> {unit, min, max, higher_is_better, integer}
GAME_CAPABILITIES = {
    "typing": {
        "metrics": {
            "wpm":        {"unit": "wpm",       "min": 10,  "max": 150, "higher_is_better": True,  "integer": True},
            "accuracy":   {"unit": "%",         "min": 70,  "max": 100, "higher_is_better": True,  "integer": True},
            "completion": {"unit": "words",     "min": 10,  "max": 200, "higher_is_better": True,  "integer": True},
        },
        "default_metric": "wpm",
    },
    "reaction": {
        "metrics": {
            "ms": {"unit": "ms", "min": 150, "max": 400, "higher_is_better": False, "integer": True},
        },
        "default_metric": "ms",
    },
    "cps": {
        "metrics": {
            "cps": {"unit": "cps", "min": 2, "max": 15, "higher_is_better": True, "integer": False},
        },
        "default_metric": "cps",
    },
    "aim3d": {
        "metrics": {
            "score":    {"unit": "points", "min": 100,  "max": 5000, "higher_is_better": True,  "integer": True},
            "accuracy": {"unit": "%",      "min": 20,   "max": 100,  "higher_is_better": True,  "integer": True},
        },
        "default_metric": "score",
    },
    "memory": {
        "metrics": {
            "level":     {"unit": "level",    "min": 1,  "max": 12, "higher_is_better": True, "integer": True},
            "sequence":  {"unit": "items",    "min": 3,  "max": 30, "higher_is_better": True, "integer": True},
            "mistakes":  {"unit": "mistakes", "min": 0,  "max": 10, "higher_is_better": False, "integer": True},
        },
        "default_metric": "level",
    },
    "tictactoe": {
        "metrics": {
            "win": {"unit": "wins", "min": 1, "max": 1, "higher_is_better": True, "integer": True},
        },
        "default_metric": "win",
    },
    "runner": {
        "metrics": {
            "score":    {"unit": "points", "min": 5,  "max": 1000, "higher_is_better": True, "integer": True},
            "distance": {"unit": "m",      "min": 50, "max": 5000, "higher_is_better": True, "integer": True},
        },
        "default_metric": "score",
    },
    "fitness": {
        "metrics": {
            "reps":     {"unit": "reps",    "min": 5,   "max": 200, "higher_is_better": True, "integer": True},
            "time":     {"unit": "seconds", "min": 15,  "max": 600, "higher_is_better": True, "integer": True},
            "distance": {"unit": "km",      "min": 0.5, "max": 20,  "higher_is_better": True, "integer": False},
        },
        "default_metric": "reps",
    },
    "quiz": {
        "metrics": {
            "score":    {"unit": "correct", "min": 3,  "max": 10, "higher_is_better": True, "integer": True},
            "accuracy": {"unit": "%",       "min": 40, "max": 100, "higher_is_better": True, "integer": True},
        },
        "default_metric": "score",
    },
}

# Metric-name aliases the AI might emit. Keys are canonical metric names.
METRIC_ALIASES = {
    "wpm":        {"wpm", "speed", "typing speed", "words per minute", "words/minute", "words per min"},
    "accuracy":   {"accuracy", "acc", "precision", "accurate", "accuracy rate"},
    "ms":         {"ms", "reaction", "reaction time", "milliseconds", "response time", "reflex time"},
    "cps":        {"cps", "clicks per second", "click speed", "clicks/sec", "cps rate"},
    "score":      {"score", "points", "high score", "final score"},
    "level":      {"level", "levels", "game level"},
    "sequence":   {"sequence", "items", "cards", "card sequence"},
    "mistakes":   {"mistakes", "errors", "wrong moves"},
    "completion": {"completion", "words", "passage", "complete"},
    "reps":       {"reps", "repetitions", "rep count", "reps count"},
    "time":       {"time", "seconds", "duration", "survive"},
    "distance":   {"distance", "km", "miles", "meters", "metres"},
    "win":        {"win", "wins", "victory", "beat"},
}


def metric_info(game_key, metric):
    cap = GAME_CAPABILITIES.get(game_key)
    if not cap:
        return None
    return cap.get("metrics", {}).get(metric)


def default_metric(game_key):
    cap = GAME_CAPABILITIES.get(game_key)
    if not cap:
        return None
    return cap.get("default_metric")


def normalize_metric(game_key, raw_metric):
    """Map an AI-supplied metric name onto a supported canonical metric."""
    if not raw_metric:
        return default_metric(game_key)
    raw = str(raw_metric).strip().lower()
    for canonical, aliases in METRIC_ALIASES.items():
        if raw in aliases or raw == canonical:
            if metric_info(game_key, canonical):
                return canonical
    if metric_info(game_key, raw):
        return raw
    for canonical, aliases in METRIC_ALIASES.items():
        for a in aliases:
            if a in raw or raw in a:
                if metric_info(game_key, canonical):
                    return canonical
    return default_metric(game_key)


def clamp_target(game_key, metric, target):
    """Clamp a numeric target into the game's supported bounds. None if unusable."""
    info = metric_info(game_key, metric)
    if not info:
        return None
    try:
        t = float(target)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(t):
        return None
    t = max(info["min"], min(info["max"], t))
    if info.get("integer"):
        t = int(round(t))
    else:
        t = round(t, 2)
    return t


def human_objective(game_key, metric, target):
    """Build a short, clear objective phrase from structured fields."""
    if game_key == "tictactoe":
        return "Win a game against the AI"
    if target is None:
        return "Complete the challenge"
    info = metric_info(game_key, metric)
    unit = info["unit"] if info else ""
    higher = info["higher_is_better"] if info else True
    if game_key == "reaction" or not higher:
        return f"Score {target}{unit} or faster" if metric == "ms" else f"Keep it at {target}{unit} or better"
    return f"Reach {target} {unit}"


def validate_challenge(cd):
    """
    Validate and normalize an AI challenge's structured fields against the
    capability map. Mutates nothing; returns (cleaned, problems).

    Only games in GAME_CAPABILITIES are enforced. Offline/external challenges
    (coding, art, web, fitness by category) keep their objective freeform.
    """
    problems = []
    game_key = (cd.get("game_key") or "").strip().lower()
    if game_key.startswith("web:"):
        game_key = ""
    cleaned = dict(cd)

    if game_key not in GAME_CAPABILITIES:
        # Freeform objective, no enforcement
        cleaned["objective"] = cleaned.get("objective") or cleaned.get("description") or "Complete the challenge"
        cleaned["metric"] = cleaned.get("metric") or ""
        cleaned["target"] = cleaned.get("target")
        cleaned["unit"] = cleaned.get("unit") or ""
        return cleaned, problems

    metric = normalize_metric(game_key, cleaned.get("metric"))
    if not metric:
        metric = default_metric(game_key)
    cleaned["metric"] = metric

    target = cleaned.get("target")
    clamped = clamp_target(game_key, metric, target)
    if target is not None and clamped is None:
        problems.append(f"Unsupported target for {game_key}.{metric}")
    if clamped is not None:
        if target is not None and float(clamped) != float(target):
            problems.append(f"Target {target} clamped to {clamped}")
        cleaned["target"] = clamped
        info = metric_info(game_key, metric)
        cleaned["unit"] = cleaned.get("unit") or (info["unit"] if info else "")
    else:
        cleaned["target"] = None

    if not cleaned.get("objective"):
        cleaned["objective"] = human_objective(game_key, cleaned["metric"], cleaned.get("target"))
    return cleaned, problems
