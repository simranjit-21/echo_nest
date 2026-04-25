from __future__ import annotations

import json
import logging
import os
import time
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Entry

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
DEFAULT_HTTP_TIMEOUT = 6
logger = logging.getLogger(__name__)
_CACHE_TTL_SECONDS = 900
_cache_store: dict[tuple[str, str, int], tuple[float, list[dict[str, str]]]] = {}


def _json_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
    form_data: str | None = None,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> dict[str, object]:
    request_headers = headers.copy() if headers else {}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    elif form_data is not None:
        body = form_data.encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    request = Request(url, data=body, method=method, headers=request_headers)
    with urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    if not raw:
        return {}
    return json.loads(raw)


def analyze_journal_with_llm(entries: list[Entry], user_message: str = "") -> dict[str, object] | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    if not api_key:
        return None

    recent_entries = entries[-8:]
    notes_payload = [
        {
            "date": entry.entry_date.isoformat(),
            "mood": entry.mood,
            "state": entry.emotion_state or "calm",
            "sleep_hours": entry.sleep_hours,
            "activities": entry.activities or "",
            "notes": entry.notes or "",
        }
        for entry in recent_entries
    ]
    prompt = {
        "recent_entries": notes_payload,
        "user_message": user_message,
        "task": (
            "You are a supportive wellness journaling assistant. Analyze the user's recent emotional patterns. "
            "Return strict JSON with keys: summary, patterns, recurring_concerns, emotional_insight, prompt. "
            "Each list should have at most 3 short strings. Be empathetic, specific, and avoid medical claims."
        ),
    }

    try:
        response = _json_request(
            OPENAI_CHAT_URL,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
            },
            payload={
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only valid JSON and keep recommendations supportive and practical.",
                    },
                    {"role": "user", "content": json.dumps(prompt)},
                ],
            },
        )
        content = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        parsed = json.loads(content) if isinstance(content, str) and content else None
        if not isinstance(parsed, dict):
            return None
        return {
            "summary": str(parsed.get("summary", "")).strip(),
            "patterns": [str(item).strip() for item in parsed.get("patterns", [])[:3]],
            "recurring_concerns": [
                str(item).strip() for item in parsed.get("recurring_concerns", [])[:3]
            ],
            "emotional_insight": str(parsed.get("emotional_insight", "")).strip(),
            "prompt": str(parsed.get("prompt", "")).strip(),
            "source": f"openai:{model}",
        }
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
        logger.warning("OpenAI journal analysis failed, falling back to local rules.")
        return None


@lru_cache(maxsize=1)
def _spotify_access_token() -> str | None:
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None

    auth = f"{client_id}:{client_secret}".encode("utf-8")
    import base64

    try:
        response = _json_request(
            SPOTIFY_TOKEN_URL,
            method="POST",
            headers={
                "Authorization": f"Basic {base64.b64encode(auth).decode('ascii')}",
            },
            form_data="grant_type=client_credentials",
        )
    except (HTTPError, URLError, TimeoutError, ValueError):
        logger.warning("Spotify token request failed.")
        return None
    token = response.get("access_token")
    return str(token).strip() if token else None


def fetch_spotify_recommendations(query: str, limit: int = 2) -> list[dict[str, str]]:
    cache_key = ("spotify", query, limit)
    cached = _cache_store.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    token = _spotify_access_token()
    if not token:
        return []

    params = urlencode({"q": query, "type": "playlist", "limit": limit})
    try:
        response = _json_request(
            f"{SPOTIFY_SEARCH_URL}?{params}",
            headers={"Authorization": f"Bearer {token}"},
        )
    except (HTTPError, URLError, TimeoutError, ValueError):
        logger.warning("Spotify recommendations failed for query '%s'.", query)
        return []

    items = response.get("playlists", {}).get("items", [])
    results: list[dict[str, str]] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        external_urls = item.get("external_urls", {})
        results.append(
            {
                "title": str(item.get("name", "Spotify playlist")).strip(),
                "url": str(external_urls.get("spotify", "")).strip(),
                "source": "spotify",
            }
        )
    filtered = [result for result in results if result["url"]]
    _cache_store[cache_key] = (time.time(), filtered)
    return filtered


def fetch_youtube_recommendations(query: str, limit: int = 2) -> list[dict[str, str]]:
    cache_key = ("youtube", query, limit)
    cached = _cache_store.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        return []

    params = urlencode(
        {
            "part": "snippet",
            "maxResults": limit,
            "q": query,
            "type": "video",
            "key": api_key,
        }
    )
    try:
        response = _json_request(f"{YOUTUBE_SEARCH_URL}?{params}")
    except (HTTPError, URLError, TimeoutError, ValueError):
        logger.warning("YouTube recommendations failed for query '%s'.", query)
        return []

    items = response.get("items", [])
    results: list[dict[str, str]] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        if not video_id:
            continue
        results.append(
            {
                "title": str(snippet.get("title", "YouTube recommendation")).strip(),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "source": "youtube",
            }
        )
    _cache_store[cache_key] = (time.time(), results)
    return results
