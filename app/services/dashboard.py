from __future__ import annotations

from collections import Counter
from datetime import timedelta
from statistics import mean

from ..models import Entry
from .emotion import build_micro_activity, state_payload


def tokenize_entry_activities(entries: list[Entry]) -> list[str]:
    tokens: list[str] = []
    for entry in entries:
        if not entry.activities:
            continue
        for raw_part in entry.activities.split(","):
            token = raw_part.strip().lower()
            if token:
                tokens.append(token)
    return tokens


def build_realtime_suggestions(
    dominant_state_key: str,
    average_sleep: float,
    average_interaction: float,
    top_activities: list[dict[str, object]],
    trend_label: str,
) -> list[str]:
    suggestions: list[str] = []
    if dominant_state_key in {"sad", "gloomy"}:
        suggestions.append(
            "Favor one low-friction reset today: sunlight, water, and a ten-minute walk before another screen session."
        )
    if dominant_state_key == "angry":
        suggestions.append(
            "Shift high-friction conversations by fifteen minutes and do one body reset first: breathing, stretching, or a fast hallway walk."
        )
    if dominant_state_key == "focus":
        suggestions.append(
            "Protect a single 45-minute deep-work block while your focus state is available."
        )
    if dominant_state_key in {"peace", "calm"}:
        suggestions.append(
            "Keep the rhythm stable by repeating the activity that helped you settle most recently."
        )
    if dominant_state_key in {"energy", "happiness"}:
        suggestions.append(
            "Use the higher-energy window for something social or creative before the state cools."
        )
    if average_sleep and average_sleep < 6.5:
        suggestions.append(
            "Sleep is under your steady-state range, so tonight's easiest win is an earlier screen cutoff."
        )
    if average_interaction and average_interaction < 2.5:
        suggestions.append(
            "Your interaction rhythm is low; a short check-in with one trusted person may lift the baseline."
        )
    if top_activities:
        suggestions.append(
            f"{top_activities[0]['name']} is acting like an anchor. Repeat it intentionally when your state dips."
        )
    if trend_label == "Cooling":
        suggestions.append(
            "Your recent trend is cooling, so favor recovery inputs over performance goals for the next check-in."
        )
    return suggestions[:3] or [
        "Keep logging sleep, interactions, and activities so Echo_Nest can sharpen its suggestions."
    ]


def build_weekly_reflection(entries: list[Entry]) -> dict[str, object]:
    if not entries:
        return {
            "headline": "Weekly reflection unlocks after a few entries.",
            "wins": [],
            "watchouts": [],
            "next_step": "Add three check-ins across the week to generate a clearer reflection.",
        }

    recent = entries[-7:]
    state_counts = Counter(entry.emotion_state or "calm" for entry in recent)
    top_state = state_counts.most_common(1)[0][0]
    activity_counts = Counter(tokenize_entry_activities(recent))
    wins: list[str] = []
    watchouts: list[str] = []

    avg_sleep = round(
        mean([entry.sleep_hours for entry in recent if entry.sleep_hours is not None]), 1
    ) if any(entry.sleep_hours is not None for entry in recent) else 0.0

    if activity_counts:
        activity_name, count = activity_counts.most_common(1)[0]
        wins.append(f"{activity_name.title()} showed up {count} times and looks like a stabilizing anchor.")
    if avg_sleep >= 7:
        wins.append(f"Average sleep held at {avg_sleep} hours, which supported steadier recovery.")
    elif avg_sleep:
        watchouts.append(f"Average sleep landed at {avg_sleep} hours, so recovery may be underpowered.")

    if top_state in {"sad", "angry", "gloomy"}:
        watchouts.append(
            f"The week leaned {state_payload(top_state)['label'].lower()}, so lower-friction care is worth prioritizing."
        )
    else:
        wins.append(
            f"The week most often read as {state_payload(top_state)['label'].lower()}, which gives you a steadier base to build on."
        )

    next_step = (
        "Repeat your best anchor on purpose and protect sleep before adding extra goals."
        if watchouts
        else "Keep repeating the routines that created stability, and capture why they worked."
    )
    return {
        "headline": f"This week mostly felt {state_payload(top_state)['label'].lower()}.",
        "wins": wins[:3],
        "watchouts": watchouts[:3],
        "next_step": next_step,
    }


def build_historical_analytics(entries: list[Entry]) -> dict[str, object]:
    if len(entries) < 3:
        return {
            "headline": "Historical analytics unlock after a few more entries.",
            "signals": [],
        }

    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    mood_by_weekday: dict[int, list[int]] = {}
    for entry in entries:
        mood_by_weekday.setdefault(entry.entry_date.weekday(), []).append(entry.mood)

    best_weekday = max(mood_by_weekday.items(), key=lambda item: mean(item[1]))
    toughest_weekday = min(mood_by_weekday.items(), key=lambda item: mean(item[1]))
    recent_month = entries[-30:]
    low_then_recovered = 0
    for previous, current in zip(entries, entries[1:]):
        if previous.mood <= 2 and current.mood >= 4:
            low_then_recovered += 1

    average_screen = round(
        mean([entry.screen_time_hours for entry in recent_month if entry.screen_time_hours is not None]), 1
    ) if any(entry.screen_time_hours is not None for entry in recent_month) else 0.0
    average_sleep = round(
        mean([entry.sleep_hours for entry in recent_month if entry.sleep_hours is not None]), 1
    ) if any(entry.sleep_hours is not None for entry in recent_month) else 0.0
    monthly_delta = recent_month[-1].mood - recent_month[0].mood if len(recent_month) >= 2 else 0

    signals = [
        f"Best weekday so far: {weekday_names[best_weekday[0]]} ({mean(best_weekday[1]):.1f}/5 average mood).",
        f"Most fragile weekday: {weekday_names[toughest_weekday[0]]} ({mean(toughest_weekday[1]):.1f}/5 average mood).",
        f"Recovery spikes after low days happened {low_then_recovered} times in your history.",
    ]
    if average_sleep:
        signals.append(f"Average recent sleep is {average_sleep} hours.")
    if average_screen:
        signals.append(f"Average recent screen time is {average_screen} hours.")
    if monthly_delta:
        direction = "up" if monthly_delta > 0 else "down"
        signals.append(f"Your last-month mood ended {direction} {abs(monthly_delta)} point(s) from where it began.")

    return {
        "headline": "Longer-range patterns across your recent history.",
        "signals": signals[:5],
    }


def build_dashboard_summary(entries: list[Entry]) -> dict[str, object]:
    if not entries:
        return {
            "entry_count": 0,
            "average_mood": 0.0,
            "current_streak": 0,
            "trend_label": "Start logging to unlock your climate story.",
            "dominant_state": state_payload("calm"),
            "top_activities": [],
            "average_sleep": 0.0,
            "average_interaction": 0.0,
            "state_breakdown": [],
            "realtime_suggestions": [
                "Add three entries with sleep and activity context to unlock more specific suggestions.",
                "Try a two-minute breathing reset to establish a calmer baseline.",
            ],
            "micro_activity": build_micro_activity("calm"),
            "climate_note": "Your dashboard will turn into a weekly reflection once you add a few entries.",
            "latest_state_key": "calm",
            "weekly_reflection": build_weekly_reflection([]),
            "historical_analytics": build_historical_analytics([]),
        }

    moods = [entry.mood for entry in entries]
    average_mood = round(sum(moods) / len(moods), 1)
    current_streak = 1
    for idx in range(len(moods) - 1, 0, -1):
        if moods[idx] >= 4 and moods[idx - 1] >= 4:
            current_streak += 1
        else:
            break

    recent_slice = moods[-3:] if len(moods) >= 3 else moods
    earlier_slice = moods[:-3] if len(moods) > 3 else moods[:1]
    recent_avg = sum(recent_slice) / len(recent_slice)
    earlier_avg = sum(earlier_slice) / len(earlier_slice)
    delta = recent_avg - earlier_avg
    if delta >= 0.35:
        trend_label = "Rising"
    elif delta <= -0.35:
        trend_label = "Cooling"
    else:
        trend_label = "Stable"

    state_counts = Counter(entry.emotion_state or "calm" for entry in entries)
    dominant_state_key = state_counts.most_common(1)[0][0]
    top_activities = [
        {"name": name.title(), "count": count}
        for name, count in Counter(tokenize_entry_activities(entries)).most_common(3)
    ]
    sleep_values = [entry.sleep_hours for entry in entries if entry.sleep_hours is not None]
    interaction_values = [
        entry.interaction_level for entry in entries if entry.interaction_level is not None
    ]
    average_sleep = round(mean(sleep_values), 1) if sleep_values else 0.0
    average_interaction = round(mean(interaction_values), 1) if interaction_values else 0.0
    state_breakdown = [
        {**state_payload(state_key), "count": count}
        for state_key, count in state_counts.most_common()
    ]
    realtime_suggestions = build_realtime_suggestions(
        dominant_state_key,
        average_sleep,
        average_interaction,
        top_activities,
        trend_label,
    )
    micro_activity = build_micro_activity(dominant_state_key)

    note_parts = [
        f"Your average mood sits at {average_mood}/5, with the overall climate feeling {trend_label.lower()}.",
        f"The dominant emotional state this period is {state_payload(dominant_state_key)['label'].lower()}.",
    ]
    if top_activities:
        note_parts.append(
            f"Your strongest anchors are {', '.join(activity['name'] for activity in top_activities)}."
        )
    if average_sleep:
        note_parts.append(
            f"Average sleep is {average_sleep} hours, which is feeding the tone of your check-ins."
        )
    if average_interaction:
        note_parts.append(f"Your social interaction rhythm is {average_interaction}/5.")
    if current_streak >= 2:
        note_parts.append(
            f"You are on a {current_streak}-entry bright streak worth calling out in your presentation."
        )
    else:
        note_parts.append("A few more consistent check-ins will make the trend story even stronger.")

    return {
        "entry_count": len(entries),
        "average_mood": average_mood,
        "current_streak": current_streak if moods[-1] >= 4 else 0,
        "trend_label": trend_label,
        "dominant_state": state_payload(dominant_state_key),
        "top_activities": top_activities,
        "average_sleep": average_sleep,
        "average_interaction": average_interaction,
        "state_breakdown": state_breakdown,
        "realtime_suggestions": realtime_suggestions,
        "micro_activity": micro_activity,
        "climate_note": " ".join(note_parts),
        "latest_state_key": entries[-1].emotion_state or dominant_state_key,
        "weekly_reflection": build_weekly_reflection(entries),
        "historical_analytics": build_historical_analytics(entries),
    }
