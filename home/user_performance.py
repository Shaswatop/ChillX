from datetime import date, timedelta
from .models import Challenge
from django.db.models import Avg, Count, Q


# Summarizes how the user does in challenges (pass rates, etc).
# If removed, the AI has no info to tailor challenges.
# Used when generating daily challenges.
def get_user_performance_summary(user):
    qs = Challenge.objects.filter(user=user)
    total = qs.count()
    if total == 0:
        return {
            "is_new": True,
            "total_completed": 0,
            "total_failed": 0,
            "total_rerolled": 0,
            "pass_rate": 0,
            "categories": {},
            "difficulties": {},
            "strong_categories": [],
            "weak_categories": [],
            "recent_trend": "stable",
            "preferred_proof_type": "text",
        }

    completed = qs.filter(status="completed")
    failed = qs.filter(status="submitted")  # submitted but not passed
    rerolled = qs.filter(status="expired")  # expired via reroll

    # per-category breakdown
    per_cat = {}
    for cat in qs.values_list("category", flat=True).distinct():
        cat_qs = qs.filter(category=cat)
        c = cat_qs.filter(status="completed").count()
        f = cat_qs.filter(status="submitted").count()
        total_cat = c + f
        if total_cat > 0:
            avg_score = cat_qs.filter(quality_score__isnull=False).aggregate(
                a=Avg("quality_score")
            )["a"] or 0
            per_cat[cat] = {
                "passed": c,
                "failed": f,
                "total": total_cat,
                "pass_rate": round(c / total_cat, 2),
                "avg_score": round(avg_score, 1),
            }

    # per-difficulty breakdown
    per_diff = {}
    for diff in ["easy", "medium", "hard", "nightmare"]:
        d_qs = qs.filter(difficulty=diff)
        c = d_qs.filter(status="completed").count()
        f = d_qs.filter(status="submitted").count()
        total_d = c + f
        if total_d > 0:
            per_diff[diff] = {
                "passed": c,
                "failed": f,
                "total": total_d,
                "pass_rate": round(c / total_d, 2),
            }

    # strong and weak categories
    pool = []
    for cat, info in per_cat.items():
        if info["total"] >= 2:
            pool.append((cat, info))
    pool.sort(key=_pass_rate_key, reverse=True)

    strong = []
    for cat, info in pool[:3]:
        if info["pass_rate"] >= 0.6:
            strong.append(cat)

    weak = []
    for cat, info in pool[-3:]:
        if info["pass_rate"] < 0.4:
            weak.append(cat)

    # compare last 7 days vs the week before
    today = date.today()
    last_week = qs.filter(created_at__gte=today - timedelta(days=7))
    prior_week = qs.filter(
        created_at__gte=today - timedelta(days=14),
        created_at__lt=today - timedelta(days=7),
    )
    last_pass_rate = _safe_rate(last_week)
    prior_pass_rate = _safe_rate(prior_week)
    if last_pass_rate > prior_pass_rate + 0.1:
        trend = "improving"
    elif last_pass_rate < prior_pass_rate - 0.1:
        trend = "declining"
    else:
        trend = "stable"

    # preferred proof type: image vs text
    proof_breakdown = qs.values("proof_type").annotate(n=Count("id"))
    preferred_proof = "text"
    best = None
    for row in proof_breakdown:
        if best is None or row["n"] > best["n"]:
            best = row
    if best is not None and best["proof_type"]:
        preferred_proof = best["proof_type"]

    pass_rate = _safe_rate(qs)

    return {
        "is_new": False,
        "total_completed": completed.count(),
        "total_failed": failed.count(),
        "total_rerolled": rerolled.count(),
        "pass_rate": pass_rate,
        "categories": per_cat,
        "difficulties": per_diff,
        "strong_categories": strong,
        "weak_categories": weak,
        "recent_trend": trend,
        "preferred_proof_type": preferred_proof,
    }


# Returns the pass rate from a (category, info) tuple for sorting.
# If removed, sorting strong/weak categories crashes.
# Used when sorting categories in the summary.
def _pass_rate_key(item):
    return item[1]["pass_rate"]


# Calculates pass rate (0-1) without dividing by zero.
# If removed, pass rate and trend calculations break.
# Used in get_user_performance_summary.
def _safe_rate(qs):
    c = qs.filter(status="completed").count()
    f = qs.filter(status="submitted").count()
    total = c + f
    if total > 0:
        return round(c / total, 2)
    return 0.0


# Turns the performance summary into text the AI can read.
# If removed, the AI prompt has nothing about the user.
# Used when generating daily challenges.
def format_summary_for_prompt(user):
    import random
    s = get_user_performance_summary(user)

    if s["is_new"]:
        vibes = [
            "USER IS NEW — no challenge history yet. Make challenges welcoming and easy to start (level 1-5 range).",
            "Fresh user! Give them fun introductory challenges that showcase different game types.",
            "New challenger detected! Start with accessible, confidence-building quests.",
        ]
        return random.choice(vibes)

    lines = []
    level_label = '?'
    if hasattr(user, 'level'):
        level_label = user.level
    lines.append(f"User Lv.{level_label} | Completed {s['total_completed']} challeges, "
                 f"failed {s['total_failed']}, rerolled {s['total_rerolled']}.")
    lines.append(f"Pass rate: {int(s['pass_rate'] * 100)}%. Recent trend: {s['recent_trend']}.")
    lines.append(f"Proof preference: {s['preferred_proof_type']}.")

    # favorite category
    fav = None
    for cat, info in s["categories"].items():
        if fav is None or info["total"] > fav[1]["total"]:
            fav = (cat, info)
    if fav:
        lines.append(f"Most played category: {fav[0]} ({fav[1]['total']} times, "
                     f"{int(fav[1]['pass_rate']*100)}% pass rate).")

    # category-specific hints
    if s["strong_categories"]:
        lines.append(f"STRONG at: {', '.join(s['strong_categories'])} — push harder targets here.")
    if s["weak_categories"]:
        lines.append(f"STRUGGLES with: {', '.join(s['weak_categories'])} — offer easier/skip.")

    # trend advice
    if s["recent_trend"] == "declining":
        lines.append("User declining — generate easier/shorter challenges to rebuild momentum.")
    elif s["recent_trend"] == "improving":
        lines.append("User improving — slightly harder targets than their current level.")

    # pass rate advice
    if s["pass_rate"] < 0.3 and s["total_completed"] > 3:
        lines.append("LOW pass rate — focus on Easy wins with conservative targets.")
    elif s["pass_rate"] > 0.8 and s["total_completed"] > 3:
        lines.append("HIGH pass rate — they can handle Hard+ difficulty.")

    # encourage variety based on history
    cats_tried = []
    for cat, v in s["categories"].items():
        if v["total"] >= 1:
            cats_tried.append(cat)
    if len(cats_tried) >= 3:
        lines.append(f"User has tried {len(cats_tried)} different categories — good variety, keep mixing it up.")

    return "\n".join(lines)


# Counts consecutive days the user completed a challenge.
# If removed, streak badges and the streak display stop working.
# Called from dashboard and achievement views.
def get_streak(user):
    today = date.today()
    streak = 0
    for d in range(0, 365):
        day = today - timedelta(days=d)
        if Challenge.objects.filter(user=user, created_at=day, status="completed").exists():
            streak += 1
        else:
            break
    return streak
