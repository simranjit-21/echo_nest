from __future__ import annotations

import logging
from urllib.parse import quote_plus

from .content import companion_content
from .integrations import (
    analyze_journal_with_llm,
    fetch_spotify_recommendations,
    fetch_youtube_recommendations,
)
from .models import Entry, HabitEvent
from .services.companion_support import (
    build_cbt_interventions,
    build_debrief,
    build_local_journal_analysis,
    build_observations,
    infer_cbt_pattern,
)
from .services.gamification import build_gamification

logger = logging.getLogger(__name__)
_CONTENT = companion_content()
SUPPORTIVE_OPENERS = _CONTENT["supportive_openers"]
MICRO_ACTIVITY_LIBRARY = _CONTENT["micro_activity_library"]
MUSIC_LIBRARY = _CONTENT["music_library"]
CONCERN_MAP = {name: set(values) for name, values in _CONTENT["concern_map"].items()}
NEGATIVE_THOUGHT_MARKERS = _CONTENT["negative_thought_markers"]


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
        logger.info("Using live LLM journal analysis.")
        return llm_analysis
    return build_local_journal_analysis(entries, concern_map=CONCERN_MAP)


def build_companion_payload(
    entries: list[Entry],
    habit_events: list[HabitEvent],
    user_message: str = "",
) -> dict[str, object]:
    latest = entries[-1] if entries else None
    state_key = latest.emotion_state if latest and latest.emotion_state else "calm"
    flags, observations, sleep_average, mood_average, logging_streak, reset_streak = (
        build_observations(entries, habit_events, state_key=state_key)
    )

    journal = build_journal_analysis(entries, user_message=user_message)
    micro_activities = MICRO_ACTIVITY_LIBRARY.get(state_key, MICRO_ACTIVITY_LIBRARY["calm"])
    music = build_music_recommendations(state_key)
    gamification = build_gamification(entries, habit_events)

    combined_text = " ".join(
        part
        for part in [user_message.strip(), latest.notes.strip() if latest and latest.notes else ""]
        if part
    )
    cbt_pattern = infer_cbt_pattern(combined_text, NEGATIVE_THOUGHT_MARKERS)
    cbt_interventions = build_cbt_interventions()
    debrief = build_debrief(state_key=state_key, journal_prompt=journal["prompt"])

    response_parts = [SUPPORTIVE_OPENERS.get(state_key, SUPPORTIVE_OPENERS["calm"])]
    response_parts.extend(
        observations[:3]
        or ["Keep logging context like sleep and notes so the companion can stay specific."]
    )
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
