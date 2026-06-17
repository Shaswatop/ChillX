"""
User Performance Profile — learns from each user's challenge behavior.

This is the "training" part: every time a user passes, fails, or rerolls a
challenge, we update their profile. Future AI prompts use this profile to
generate challenges tailored to:
  - What the user is good at (boost those categories)
  - What the user struggles with (offer easier versions, or skip)
  - The user's pace (long vs short challenges)
  - The user's success trend (level up or stay put)
"""

from datetime import date, timedelta
from .models import Challenge
from django.db.models import Avg, Count, Q


def get_user_performance_summary(user) -> dict:
    """
    Build a per-user performance summary that the AI prompt uses to adapt.

    Returns a dict with:
      - total_completed, total_failed, total_rerolled
      - per_category: {cat: {passed: n, failed: n, pass_rate: 0-1, avg_score: 0-10}}
      - per_difficulty: {diff: {...}}
      - strong_categories, weak_categories  (top 3 each)
      - recent_trend (improving, stable, declining)
      - preferred_proof_type
      - avg_minutes_between_generation_and_completion
    """
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
    failed = qs.filter(status="submitted")  # submitted but not yet passed = failed
    rerolled = qs.filter(status="expired")   # expired via reroll

    # Per-category breakdown
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

    # Per-difficulty breakdown
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

    # Strong / weak categories
    sorted_cats = sorted(
        [c for c in per_cat.items() if c[1]["total"] >= 2],
        key=lambda x: x[1]["pass_rate"],
        reverse=True,
    )
    strong = [c[0] for c in sorted_cats[:3] if c[1]["pass_rate"] >= 0.6]
    weak = [c[0] for c in sorted_cats[-3:] if c[1]["pass_rate"] < 0.4]

    # Recent trend — compare last 7 days vs prior 7 days
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

    # Preferred proof type (image vs text)
    proof_breakdown = qs.values("proof_type").annotate(n=Count("id"))
    preferred_proof = "text"
    if proof_breakdown:
        top = max(proof_breakdown, key=lambda x: x["n"])
        preferred_proof = top["proof_type"] or "text"

    # Overall pass rate
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


def _safe_rate(qs) -> float:
    """Pass rate (0-1) of a Challenge queryset, safely."""
    c = qs.filter(status="completed").count()
    f = qs.filter(status="submitted").count()
    total = c + f
    return round(c / total, 2) if total > 0 else 0.0


def format_summary_for_prompt(user) -> str:
    """Format the user's performance summary as a human-readable string for the AI."""
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
    lines.append(f"User Lv.{user.level if hasattr(user, 'level') else '?'} | "
                 f"Completed {s['total_completed']} challeges, failed {s['total_failed']}, "
                 f"rerolled {s['total_rerolled']}.")
    lines.append(f"Pass rate: {int(s['pass_rate'] * 100)}%. Recent trend: {s['recent_trend']}.")
    lines.append(f"Proof preference: {s['preferred_proof_type']}.")

    # Favorite category
    if s["categories"]:
        fav = max(s["categories"].items(), key=lambda x: x[1]["total"])
        lines.append(f"Most played category: {fav[0]} ({fav[1]['total']} times, {int(fav[1]['pass_rate']*100)}% pass rate).")

    # Category-specific hints
    if s["strong_categories"]:
        lines.append(f"STRONG at: {', '.join(s['strong_categories'])} — push harder targets here.")
    if s["weak_categories"]:
        lines.append(f"STRUGGLES with: {', '.join(s['weak_categories'])} — offer easier/skip.")

    # Trend-based advice
    if s["recent_trend"] == "declining":
        lines.append("User declining — generate easier/shorter challenges to rebuild momentum.")
    elif s["recent_trend"] == "improving":
        lines.append("User improving — slightly harder targets than their current level.")

    # Pass rate advice
    if s["pass_rate"] < 0.3 and s["total_completed"] > 3:
        lines.append("LOW pass rate — focus on Easy wins with conservative targets.")
    elif s["pass_rate"] > 0.8 and s["total_completed"] > 3:
        lines.append("HIGH pass rate — they can handle Hard+ difficulty.")

    # Suggest category variety based on history
    cats_tried = [cat for cat, v in s["categories"].items() if v["total"] >= 1]
    if len(cats_tried) >= 3:
        lines.append(f"User has tried {len(cats_tried)} different categories — good variety, keep mixing it up.")

    return "\n".join(lines)


def get_streak(user) -> int:
    """Consecutive days the user has completed at least one challenge."""
    today = date.today()
    streak = 0
    for d in range(0, 365):
        day = today - timedelta(days=d)
        if Challenge.objects.filter(user=user, created_at=day, status="completed").exists():
            streak += 1
        else:
            break
    return streak
