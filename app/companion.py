from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from statistics import mean
from urllib.parse import quote_plus

from .integrations import (
    analyze_journal_with_llm,
    fetch_spotify_recommendations,
    fetch_youtube_recommendations,
)
from .models import Entry, HabitEvent

SUPPORTIVE_OPENERS = {
    "calm": "You have a steadier baseline right now, so this is a good moment to reinforce what is already working.",
    "energy": "You are carrying more activation today, which we can turn into something supportive instead of scattered.",
    "happiness": "There is some lift in your recent data, and it is worth helping that feeling stick.",
    "focus": "Your recent pattern shows usable mental clarity, so let us make the next action deliberate.",
    "peace": "Your signals look more settled, which is a good window for gentle reflection.",
    "sad": "I can see a lower emotional tone in your recent check-ins, so let us keep this response gentle and practical.",
    "angry": "Your recent pattern suggests frustration or overload, so we will start by reducing intensity before solving anything.",
    "gloomy": "Your logs suggest low energy and emotional fog, so the goal is a tiny caring action instead of pressure.",
}

MICRO_ACTIVITY_LIBRARY = {
    "calm": [
        {
            "title": "Two-minute body scan",
            "reason": "Keeps a stable baseline from drifting.",
            "duration": 120,
        },
        {
            "title": "Name three steadying things",
            "reason": "Reinforces what is already helping.",
            "duration": 90,
        },
    ],
    "energy": [
        {
            "title": "Channel the surge",
            "reason": "Use activation for one intentional win before it scatters.",
            "duration": 180,
        },
        {
            "title": "Fast reset walk",
            "reason": "Converts restless energy into momentum.",
            "duration": 180,
        },
    ],
    "happiness": [
        {
            "title": "Save the high point",
            "reason": "Turns a good moment into a memory anchor.",
            "duration": 120,
        },
        {
            "title": "Send one warm message",
            "reason": "Spreads the positive state socially.",
            "duration": 120,
        },
    ],
    "focus": [
        {
            "title": "Ten-minute single-task sprint",
            "reason": "Protects the clearest part of your attention.",
            "duration": 600,
        },
        {
            "title": "Close one tab, start one task",
            "reason": "Prevents overstimulation from interrupting focus.",
            "duration": 120,
        },
    ],
    "peace": [
        {
            "title": "Soft reflection note",
            "reason": "Helps you understand what created the calm.",
            "duration": 180,
        },
        {
            "title": "Slow exhale reset",
            "reason": "Keeps the nervous system settled.",
            "duration": 120,
        },
    ],
    "sad": [
        {
            "title": "Five-minute sunlight break",
            "reason": "Adds a low-friction lift when everything feels heavy.",
            "duration": 300,
        },
        {
            "title": "Text one safe person",
            "reason": "Creates connection without asking for a big effort.",
            "duration": 120,
        },
    ],
    "angry": [
        {
            "title": "Ninety-second decompression",
            "reason": "Lowers charge before you reply, decide, or argue.",
            "duration": 90,
        },
        {
            "title": "Cold water pause",
            "reason": "Interrupts the escalation loop physically.",
            "duration": 120,
        },
    ],
    "gloomy": [
        {
            "title": "Fog-breaker task",
            "reason": "Gives you a tiny completion when motivation is low.",
            "duration": 180,
        },
        {
            "title": "Open blinds and move",
            "reason": "Builds momentum without needing motivation first.",
            "duration": 120,
        },
    ],
}

MUSIC_LIBRARY = {
    "calm": [
        ("Acoustic grounding session", "gentle acoustic calm focus playlist"),
        ("Soft instrumental reset", "soft instrumental grounding playlist"),
    ],
    "energy": [
        ("Forward-motion mix", "motivational upbeat indie energy playlist"),
        ("Creative sprint mix", "focus electronic productivity playlist"),
    ],
    "happiness": [
        ("Sunlit serotonin mix", "feel good upbeat playlist"),
        ("Good-day groove", "happy pop groove playlist"),
    ],
    "focus": [
        ("Deep work lo-fi", "lofi beats deep focus playlist"),
        ("Minimal flow set", "minimal ambient focus playlist"),
    ],
    "peace": [
        ("Quiet evening calm", "peaceful ambient wind down playlist"),
        ("Breathing room", "healing piano calm playlist"),
    ],
    "sad": [
        ("Gentle comfort lo-fi", "comforting lofi for hard days playlist"),
        ("Soft recovery piano", "healing piano emotional reset playlist"),
    ],
    "angry": [
        ("De-escalation lo-fi", "calming lofi stress relief playlist"),
        ("Slow heartbeat ambient", "ambient breathing relaxation playlist"),
    ],
    "gloomy": [
        ("Morning lift playlist", "upbeat gentle morning energy playlist"),
        ("Tiny momentum mix", "light indie motivation playlist"),
    ],
}

CONCERN_MAP = {
    "sleep": {"tired", "insomnia", "sleep", "restless", "exhausted", "drained"},
    "stress": {"stressed", "pressure", "overwhelmed", "deadline", "burnout", "anxious"},
    "loneliness": {"alone", "lonely", "isolated", "disconnected"},
    "anger": {"angry", "frustrated", "annoyed", "resentful", "furious"},
    "self-worth": {"failure", "worthless", "useless", "behind", "not enough"},
}

NEGATIVE_THOUGHT_MARKERS = {
    "all_or_nothing": ("always", "never", "ruined", "everything"),
    "self_blame": ("my fault", "i failed", "i am the problem", "i always mess up"),
    "hopelessness": ("nothing will change", "no point", "cannot do this", "stuck"),
}


def _tokens(text: str) -> list[str]:
    return [part.strip(".,!?;:()[]\"'").lower() for part in text.split() if part.strip()]


def _consecutive_day_streak(days: list[date]) -> int:
    ordered = sorted(set(days))
    if not ordered:
        return 0

    streak = 1
    previous = ordered[-1]
    for current in reversed(ordered[:-1]):
        if previous - current == timedelta(days=1):
            streak += 1
            previous = current
            continue
        break
    return streak


def _recent_average(values: list[float], fallback: float = 0.0) -> float:
    return round(mean(values), 1) if values else fallback


def build_music_recommendations(state_key: str) -> list[dict[str, str]]:
    selections = MUSIC_LIBRARY.get(state_key, MUSIC_LIBRARY["calm"])
    recommendations: list[dict[str, str]] = []
    for title, query in selections:
        spotify_results = fetch_spotify_recommendations(query, limit=1)
        youtube_results = fetch_youtube_recommendations(query, limit=1)
        encoded = quote_plus(query)
        recommendations.append(
            {
                "title": spotify_results[0]["title"] if spotify_results else title,
                "reason": (
                    f"Matched to a {state_key} state via live providers."
                    if spotify_results or youtube_results
                    else f"Matched to a {state_key} state."
                ),
                "spotify_url": (
                    spotify_results[0]["url"]
                    if spotify_results
                    else f"https://open.spotify.com/search/{encoded}"
                ),
                "youtube_url": (
                    youtube_results[0]["url"]
                    if youtube_results
                    else f"https://www.youtube.com/results?search_query={encoded}"
                ),
                "live": bool(spotify_results or youtube_results),
            }
        )
    return recommendations


def build_journal_analysis(entries: list[Entry], user_message: str = "") -> dict[str, object]:
    llm_analysis = analyze_journal_with_llm(entries, user_message=user_message)
    if llm_analysis:
        return llm_analysis

    notes = [entry.notes.strip() for entry in entries if entry.notes and entry.notes.strip()]
    if not notes:
        return {
            "summary": "Journal insights will appear once you add a few notes to your check-ins.",
            "patterns": [],
            "recurring_concerns": [],
            "emotional_insight": "No written reflections yet, so the companion is only reading mood and habit signals.",
            "prompt": "Write one sentence about what most shaped your energy today.",
            "source": "local-rules",
        }

    token_counts = Counter()
    concern_counts = Counter()
    for note in notes:
        tokens = _tokens(note)
        token_counts.update(token for token in tokens if len(token) > 3)
        for concern, keywords in CONCERN_MAP.items():
            if any(keyword in tokens for keyword in keywords):
                concern_counts[concern] += 1

    patterns = [token.replace("_", " ").title() for token, _ in token_counts.most_common(3)]
    recurring_concerns = [name.replace("_", " ").title() for name, _ in concern_counts.most_common(3)]
    latest_notes = notes[-3:]
    reflective_shift = "Recent notes still feel mixed, so the best next step is a short reset plus one compassionate thought check."
    if any(word in " ".join(latest_notes).lower() for word in ("calm", "better", "hopeful", "clear", "grateful")):
        reflective_shift = "Your recent notes show signs of recovery language, which suggests your coping routines are starting to land."

    summary_bits = []
    if recurring_concerns:
        summary_bits.append(f"Recurring concerns: {', '.join(recurring_concerns)}.")
    if patterns:
        summary_bits.append(f"Repeated themes in your writing: {', '.join(patterns)}.")
    summary_bits.append(reflective_shift)

    prompt_focus = recurring_concerns[0].lower() if recurring_concerns else "energy"
    return {
        "summary": " ".join(summary_bits),
        "patterns": patterns,
        "recurring_concerns": recurring_concerns,
        "emotional_insight": reflective_shift,
        "prompt": f"What happened right before your {prompt_focus} felt hardest today, and what helped even a little?",
        "source": "local-rules",
    }


def build_gamification(entries: list[Entry], habit_events: list[HabitEvent]) -> dict[str, object]:
    today = date.today()
    weekly_start = today - timedelta(days=6)
    weekly_resets = [event for event in habit_events if event.occurred_on >= weekly_start]
    weekly_goal_target = 4

    log_days = [entry.entry_date for entry in entries]
    reset_days = [event.occurred_on for event in habit_events]
    logging_streak = _consecutive_day_streak(log_days)
    reset_streak = _consecutive_day_streak(reset_days)
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


def build_companion_payload(
    entries: list[Entry],
    habit_events: list[HabitEvent],
    user_message: str = "",
) -> dict[str, object]:
    latest = entries[-1] if entries else None
    state_key = (latest.emotion_state if latest and latest.emotion_state else "calm")
    recent_entries = entries[-5:]
    recent_sleep = [entry.sleep_hours for entry in recent_entries if entry.sleep_hours is not None]
    recent_moods = [entry.mood for entry in recent_entries]
    sleep_average = _recent_average(recent_sleep)
    mood_average = _recent_average([float(value) for value in recent_moods], fallback=3.0)
    logging_streak = _consecutive_day_streak([entry.entry_date for entry in entries])
    reset_streak = _consecutive_day_streak([event.occurred_on for event in habit_events])

    flags: list[str] = []
    observations: list[str] = []

    if sleep_average and sleep_average < 6.5:
        flags.append("poor_sleep")
        observations.append(
            f"Your recent sleep average is {sleep_average} hours, which often makes stress and sadness feel louder."
        )

    if len(recent_moods) >= 4:
        earlier_avg = mean(recent_moods[:2])
        later_avg = mean(recent_moods[-2:])
        if later_avg + 0.75 < earlier_avg:
            flags.append("streak_drop")
            observations.append(
                "Your mood trend dipped across the last few check-ins, so this is a good time to lower the bar and protect recovery."
            )

    if state_key in {"sad", "angry", "gloomy"}:
        flags.append("needs_debrief")
        observations.append(
            f"Your latest emotional state reads as {state_key}, so I would treat the next few minutes like a recovery window instead of a performance window."
        )

    if logging_streak >= 3:
        observations.append(f"You also have a {logging_streak}-day logging streak, which shows real consistency even if the mood signal is uneven.")
    if reset_streak >= 2:
        observations.append(f"Your reset streak is {reset_streak} days, so your coping system is already becoming a habit.")

    journal = build_journal_analysis(entries, user_message=user_message)
    micro_activities = MICRO_ACTIVITY_LIBRARY.get(state_key, MICRO_ACTIVITY_LIBRARY["calm"])
    music = build_music_recommendations(state_key)
    gamification = build_gamification(entries, habit_events)

    combined_text = " ".join(
        part for part in [user_message.strip(), latest.notes.strip() if latest and latest.notes else ""] if part
    ).lower()
    cbt_pattern = "all_or_nothing"
    for key, markers in NEGATIVE_THOUGHT_MARKERS.items():
        if any(marker in combined_text for marker in markers):
            cbt_pattern = key
            break

    cbt_interventions = {
        "all_or_nothing": {
            "thought": "This sounds like an all-or-nothing thought.",
            "reframe": "What evidence says the whole day is ruined, and what evidence says this is one hard moment inside a bigger day?",
            "replacement": "Something difficult happened, but one hard stretch does not erase every useful thing I can still do next.",
        },
        "self_blame": {
            "thought": "You may be carrying more blame than the situation actually deserves.",
            "reframe": "If a friend described the same situation, would you hold them to the same harsh standard?",
            "replacement": "I can own my part without turning the whole story into a verdict about my worth.",
        },
        "hopelessness": {
            "thought": "This sounds like hopelessness talking from a depleted place.",
            "reframe": "What is one tiny sign that your state can shift, even if the whole problem is not solved yet?",
            "replacement": "I do not need certainty right now; I only need one next action that gives me a little more room.",
        },
    }

    debrief = {
        "title": "Session Debrief",
        "summary": (
            "Your last emotional check-in suggests the priority is regulation first, analysis second."
            if state_key in {"sad", "angry", "gloomy"}
            else "Your recent pattern is steady enough to support a short reflective check-in."
        ),
        "coach_prompt": journal["prompt"],
    }

    response_parts = [SUPPORTIVE_OPENERS.get(state_key, SUPPORTIVE_OPENERS["calm"])]
    response_parts.extend(observations[:3] or ["Keep logging context like sleep and notes so the companion can stay specific."])
    response_parts.append(f"Journal insight: {journal['emotional_insight']}")

    return {
        "state": state_key,
        "flags": flags,
        "response": " ".join(response_parts),
        "micro_activities": micro_activities,
        "cbt": cbt_interventions[cbt_pattern],
        "debrief": debrief,
        "music": music,
        "journal": journal,
        "gamification": gamification,
        "snapshot": {
            "sleep_average": sleep_average,
            "mood_average": mood_average,
            "logging_streak": logging_streak,
            "reset_streak": reset_streak,
        },
        "integrations": {
            "journal_source": journal.get("source", "local-rules"),
            "music_live": any(item.get("live") for item in music),
        },
    }
