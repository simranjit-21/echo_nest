from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from statistics import mean

from ..models import Entry, HabitEvent


def tokenize_text(text: str) -> list[str]:
    return [part.strip(".,!?;:()[]\"'").lower() for part in text.split() if part.strip()]


def consecutive_day_streak(days: list[date]) -> int:
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


def recent_average(values: list[float], fallback: float = 0.0) -> float:
    return round(mean(values), 1) if values else fallback


def build_local_journal_analysis(
    entries: list[Entry],
    *,
    concern_map: dict[str, set[str]],
) -> dict[str, object]:
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
        tokens = tokenize_text(note)
        token_counts.update(token for token in tokens if len(token) > 3)
        for concern, keywords in concern_map.items():
            if any(keyword in tokens for keyword in keywords):
                concern_counts[concern] += 1

    patterns = [token.replace("_", " ").title() for token, _ in token_counts.most_common(3)]
    recurring_concerns = [
        name.replace("_", " ").title() for name, _ in concern_counts.most_common(3)
    ]
    latest_notes = notes[-3:]
    reflective_shift = (
        "Recent notes still feel mixed, so the best next step is a short reset plus one compassionate thought check."
    )
    if any(
        word in " ".join(latest_notes).lower()
        for word in ("calm", "better", "hopeful", "clear", "grateful")
    ):
        reflective_shift = (
            "Your recent notes show signs of recovery language, which suggests your coping routines are starting to land."
        )

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


def build_cbt_interventions() -> dict[str, dict[str, str]]:
    return {
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


def infer_cbt_pattern(text: str, markers: dict[str, list[str]]) -> str:
    lowered = text.lower()
    for key, values in markers.items():
        if any(marker in lowered for marker in values):
            return key
    return "all_or_nothing"


def build_observations(
    entries: list[Entry],
    habit_events: list[HabitEvent],
    *,
    state_key: str,
) -> tuple[list[str], list[str], float, float, int, int]:
    recent_entries = entries[-5:]
    recent_sleep = [entry.sleep_hours for entry in recent_entries if entry.sleep_hours is not None]
    recent_moods = [entry.mood for entry in recent_entries]
    sleep_average = recent_average(recent_sleep)
    mood_average = recent_average([float(value) for value in recent_moods], fallback=3.0)
    logging_streak = consecutive_day_streak([entry.entry_date for entry in entries])
    reset_streak = consecutive_day_streak([event.occurred_on for event in habit_events])

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
        observations.append(
            f"You also have a {logging_streak}-day logging streak, which shows real consistency even if the mood signal is uneven."
        )
    if reset_streak >= 2:
        observations.append(
            f"Your reset streak is {reset_streak} days, so your coping system is already becoming a habit."
        )
    return flags, observations, sleep_average, mood_average, logging_streak, reset_streak


def build_debrief(*, state_key: str, journal_prompt: str) -> dict[str, str]:
    return {
        "title": "Session Debrief",
        "summary": (
            "Your last emotional check-in suggests the priority is regulation first, analysis second."
            if state_key in {"sad", "angry", "gloomy"}
            else "Your recent pattern is steady enough to support a short reflective check-in."
        ),
        "coach_prompt": journal_prompt,
    }
