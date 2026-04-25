from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from ..models import Entry, HabitEvent
from .companion_support import consecutive_day_streak


def build_gamification(entries: list[Entry], habit_events: list[HabitEvent]) -> dict[str, object]:
    today = date.today()
    weekly_start = today - timedelta(days=6)
    weekly_resets = [event for event in habit_events if event.occurred_on >= weekly_start]
    weekly_goal_target = 4

    log_days = [entry.entry_date for entry in entries]
    reset_days = [event.occurred_on for event in habit_events]
    logging_streak = consecutive_day_streak(log_days)
    reset_streak = consecutive_day_streak(reset_days)
    total_points = len(entries) * 5 + sum(event.points for event in habit_events)

    recent_sleep = [entry.sleep_hours for entry in entries[-5:] if entry.sleep_hours is not None]
    recovered_after_low = False
    if len(entries) >= 2:
        previous_states = [entry.emotion_state or "calm" for entry in entries[:-1]]
        recovered_after_low = any(state in {"sad", "angry", "gloomy"} for state in previous_states) and (
            (entries[-1].emotion_state or "calm") in {"calm", "focus", "peace", "happiness", "energy"}
        )

    badges = [
        {
            "title": "Consistency Spark",
            "earned": logging_streak >= 3,
            "description": "Log your mood on three consecutive days.",
        },
        {
            "title": "Reset Builder",
            "earned": len(habit_events) >= 3,
            "description": "Complete three adaptive resets.",
        },
        {
            "title": "Sleep Guardian",
            "earned": len(recent_sleep) >= 3 and mean(recent_sleep) >= 7,
            "description": "Average at least seven hours of sleep across recent check-ins.",
        },
        {
            "title": "Bounce Back",
            "earned": recovered_after_low,
            "description": "Return to a steadier state after a rough check-in.",
        },
    ]
    unlocked = [badge for badge in badges if badge["earned"]]
    next_badge = next((badge for badge in badges if not badge["earned"]), None)

    return {
        "total_points": total_points,
        "logging_streak": logging_streak,
        "reset_streak": reset_streak,
        "weekly_goal": {
            "title": "Mood resets completed",
            "current": len(weekly_resets),
            "target": weekly_goal_target,
            "complete": len(weekly_resets) >= weekly_goal_target,
        },
        "badges": badges,
        "unlocked_badges": unlocked,
        "next_badge": next_badge,
    }
