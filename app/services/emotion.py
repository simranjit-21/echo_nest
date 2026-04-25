from __future__ import annotations

from dataclasses import dataclass

from ..content import emotion_content

_CONTENT = emotion_content()
STATE_META: dict[str, dict[str, str]] = _CONTENT["state_meta"]
POSITIVE_SENTIMENT_TOKENS = set(_CONTENT["positive_sentiment_tokens"])
NEGATIVE_SENTIMENT_TOKENS = set(_CONTENT["negative_sentiment_tokens"])
ACTIVITY_GROUPS = {
    name: set(values) for name, values in _CONTENT["activity_groups"].items()
}
MICRO_ACTIVITIES = _CONTENT["micro_activities"]


@dataclass(frozen=True)
class EmotionExplanation:
    state_key: str
    reasons: list[str]
    signals: dict[str, object]


def tokenize_activities(activities: str) -> set[str]:
    return {token.strip().lower() for token in activities.split(",") if token.strip()}


def sentiment_score(notes: str) -> int:
    tokens = [token.strip(".,!?;:").lower() for token in notes.split()]
    positives = sum(token in POSITIVE_SENTIMENT_TOKENS for token in tokens)
    negatives = sum(token in NEGATIVE_SENTIMENT_TOKENS for token in tokens)
    return positives - negatives


def state_payload(state_key: str) -> dict[str, str]:
    meta = STATE_META.get(state_key, STATE_META["calm"])
    return {
        "key": state_key,
        "label": meta["label"],
        "palette": meta["palette"],
        "description": meta["description"],
    }


def build_micro_activity(state_key: str) -> dict[str, object]:
    return MICRO_ACTIVITIES.get(state_key, MICRO_ACTIVITIES["calm"])


def classify_emotion_state(
    mood: int,
    sleep_hours: float | None,
    interaction_level: int | None,
    screen_time_hours: float | None,
    activities: str,
    notes: str = "",
) -> str:
    return explain_emotion_state(
        mood, sleep_hours, interaction_level, screen_time_hours, activities, notes
    ).state_key


def explain_emotion_state(
    mood: int,
    sleep_hours: float | None,
    interaction_level: int | None,
    screen_time_hours: float | None,
    activities: str,
    notes: str = "",
) -> EmotionExplanation:
    activity_tokens = tokenize_activities(activities)
    sleep = sleep_hours or 0.0
    interaction = interaction_level or 3
    screen_time = screen_time_hours or 0.0
    sentiment = sentiment_score(notes)

    state_key = "calm"
    reasons = [
        f"Mood intensity logged at {mood}/5.",
        f"Note sentiment scored {sentiment:+d}.",
    ]

    if mood <= 2 and sentiment <= -2:
        state_key = "sad"
        reasons.extend(
            [
                "Low mood combined with strongly negative language points to sadness.",
                "The written reflection sounds emotionally heavy rather than just tired.",
            ]
        )
    elif mood <= 2 and (sleep <= 5.5 or screen_time >= 9):
        state_key = "gloomy"
        reasons.extend(
            [
                "Low mood plus depleted recovery signals points to a gloomier state.",
                "Short sleep or very high screen time often shows up as fog rather than sharp sadness.",
            ]
        )
    elif mood <= 3 and sentiment <= -3 and interaction <= 2:
        state_key = "gloomy"
        reasons.extend(
            [
                "Negative notes plus low interaction suggest emotional fog and withdrawal.",
                "The pattern looks more flat and drained than activated.",
            ]
        )
    elif mood <= 2 and interaction >= 4 and activity_tokens & ACTIVITY_GROUPS["social"]:
        state_key = "sad"
        reasons.extend(
            [
                "Mood stayed low even with social contact, which leans toward sadness.",
                "Connection was present, but it did not fully lift the emotional tone.",
            ]
        )
    elif mood >= 3 and sentiment <= -2 and interaction >= 3 and screen_time >= 6:
        state_key = "angry"
        reasons.extend(
            [
                "Activated mood with negative language and high stimulation points to frustration.",
                "The pattern looks more charged than withdrawn.",
            ]
        )
    elif mood >= 4 and sentiment <= -1 and interaction >= 3:
        state_key = "angry"
        reasons.extend(
            [
                "High activation with negative undertones often reads as anger or overload.",
                "The emotional energy seems sharp rather than joyful.",
            ]
        )
    elif mood >= 5 or (mood >= 4 and interaction >= 4 and activity_tokens & ACTIVITY_GROUPS["social"]):
        state_key = "happiness"
        reasons.extend(
            [
                "High mood plus social energy suggests happiness.",
                "The signals show lift, openness, and positive activation.",
            ]
        )
    elif mood >= 4 and interaction >= 4:
        state_key = "energy"
        reasons.extend(
            [
                "High interaction and activation map well to an energetic state.",
                "The day looks lively and externally engaged.",
            ]
        )
    elif mood >= 3 and sleep >= 6 and (activity_tokens & ACTIVITY_GROUPS["productive"]) and screen_time <= 8:
        state_key = "focus"
        reasons.extend(
            [
                "Productive activities with decent sleep suggest focus.",
                "The signal looks clear and directed rather than simply calm.",
            ]
        )
    elif mood >= 3 and sleep >= 7.5 and interaction <= 3 and (activity_tokens & ACTIVITY_GROUPS["restorative"]):
        state_key = "peace"
        reasons.extend(
            [
                "Good sleep plus restorative activity points to peace.",
                "The emotional tone looks settled, safe, and unforced.",
            ]
        )
    else:
        reasons.extend(
            [
                "No strong distress or activation signals dominated this entry.",
                "The overall pattern reads as steady and centered.",
            ]
        )

    if sleep_hours is not None:
        reasons.append(f"Sleep contributed {sleep_hours} hours to the read.")
    if interaction_level is not None:
        reasons.append(f"Interaction level was {interaction_level}/5.")
    if screen_time_hours is not None:
        reasons.append(f"Screen time was {screen_time_hours} hours.")
    if activity_tokens:
        reasons.append(f"Activities noticed: {', '.join(sorted(activity_tokens))}.")

    return EmotionExplanation(
        state_key=state_key,
        reasons=reasons[:4],
        signals={
            "mood": mood,
            "sleep_hours": sleep_hours,
            "interaction_level": interaction_level,
            "screen_time_hours": screen_time_hours,
            "sentiment_score": sentiment,
            "activity_tokens": sorted(activity_tokens),
        },
    )
