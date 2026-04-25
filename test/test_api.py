import json
import os

import pytest
from sqlmodel import SQLModel

from app import companion as companion_module
from app import create_app, get_engine
from app.database import reset_engine_cache


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test_echo_nest.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    reset_engine_cache()

    app = create_app()
    app.config["TESTING"] = True

    engine = get_engine()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with app.test_client() as client:
        yield client

    engine.dispose()
    reset_engine_cache()
    os.environ.pop("DATABASE_URL", None)


def test_register_and_login(client):
    r = client.post(
        "/auth/register",
        data={"email": "test@example.com", "password": "secret"},
    )
    assert r.status_code == 302

    r = client.post(
        "/auth/login",
        data={"email": "test@example.com", "password": "secret"},
    )
    assert r.status_code == 302


def test_login_honors_safe_next_redirect(client):
    client.post("/auth/register", data={"email": "next@example.com", "password": "secret"})

    r = client.post(
        "/auth/login?next=/log",
        data={"email": "next@example.com", "password": "secret"},
    )

    assert r.status_code == 302
    assert r.headers["Location"].endswith("/log")


def test_login_rejects_external_next_redirect(client):
    client.post("/auth/register", data={"email": "safe@example.com", "password": "secret"})

    r = client.post(
        "/auth/login?next=https://example.com/phish",
        data={"email": "safe@example.com", "password": "secret"},
    )

    assert r.status_code == 302
    assert r.headers["Location"].endswith("/dashboard")


def test_log_and_predict(client):
    client.post("/auth/register", data={"email": "u@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "u@x.com", "password": "p"})

    for mood in [3, 4, 2, 5, 3]:
        client.post(
            "/log",
            data={
                "mood": mood,
                "activities": "walk, reading",
                "sleep_hours": "7.5",
                "interaction_level": "3",
                "screen_time_hours": "4",
                "notes": "",
            },
        )

    r = client.get("/api/predict")
    data = json.loads(r.data)
    assert "predicted_mood" in data
    assert 1 <= data["predicted_mood"] <= 5
    assert data["predicted_state"]["label"] in {
        "Calm",
        "Energy",
        "Happiness",
        "Focus",
        "Peace",
        "Sad",
        "Angry",
        "Gloomy",
    }


def test_dashboard_shows_story_metrics(client):
    client.post("/auth/register", data={"email": "story@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "story@x.com", "password": "p"})

    client.post("/log", data={"mood": "5", "activities": "music, walk", "sleep_hours": "8", "interaction_level": "5", "screen_time_hours": "2", "notes": "good"})
    client.post("/log", data={"mood": "4", "activities": "walk, reading", "sleep_hours": "7.5", "interaction_level": "3", "screen_time_hours": "4", "notes": "steady"})
    client.post("/log", data={"mood": "4", "activities": "music", "sleep_hours": "8.5", "interaction_level": "2", "screen_time_hours": "3", "notes": "calm"})

    r = client.get("/dashboard")
    body = r.get_data(as_text=True)

    assert r.status_code == 200
    assert "Emotion Spectrum" in body
    assert "Behavior Signals" in body
    assert "Adaptive Reset" in body
    assert "AI Wellness Companion" in body
    assert "Journal Intelligence" in body
    assert "Recovery Rewards" in body
    assert "Walk" in body


def test_log_saves_behavior_signals(client):
    client.post("/auth/register", data={"email": "signals@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "signals@x.com", "password": "p"})

    r = client.post(
        "/log",
        data={
            "mood": "4",
            "activities": "deep work, reading",
            "sleep_hours": "7",
            "interaction_level": "2",
            "screen_time_hours": "5",
            "notes": "locked in",
        },
        follow_redirects=False,
    )

    assert r.status_code == 302
    dashboard = client.get("/dashboard")
    body = dashboard.get_data(as_text=True)
    assert "Focus" in body or "Calm" in body


def test_negative_context_maps_to_low_emotion_states(client):
    client.post("/auth/register", data={"email": "low@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "low@x.com", "password": "p"})

    client.post(
        "/log",
        data={
            "mood": "2",
            "activities": "scrolling, alone",
            "sleep_hours": "4.5",
            "interaction_level": "1",
            "screen_time_hours": "10",
            "notes": "tired overwhelmed drained foggy",
        },
    )

    dashboard = client.get("/dashboard")
    body = dashboard.get_data(as_text=True)
    assert "Gloomy" in body or "Sad" in body
    assert "Adaptive Reset" in body


def test_capture_rejects_invalid_payload(client):
    client.post("/auth/register", data={"email": "cam@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "cam@x.com", "password": "p"})

    r = client.post("/api/capture", json={"image": "not-base64"})
    assert r.status_code == 400


def test_companion_chat_uses_context_and_returns_music(client):
    client.post("/auth/register", data={"email": "companion@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "companion@x.com", "password": "p"})

    client.post(
        "/log",
        data={
            "mood": "2",
            "activities": "scrolling, alone",
            "sleep_hours": "4.5",
            "interaction_level": "1",
            "screen_time_hours": "9",
            "notes": "I always ruin everything and feel overwhelmed",
        },
    )

    r = client.post("/api/companion/chat", json={"message": "I never handle this well"})
    data = json.loads(r.data)

    assert r.status_code == 200
    assert "poor_sleep" in data["flags"]
    assert "music" in data and len(data["music"]) >= 1
    assert "spotify_url" in data["music"][0]
    assert "all-or-nothing" in data["cbt"]["thought"].lower() or "sleep average" in data["response"].lower()


def test_habit_completion_updates_weekly_goal_and_points(client):
    client.post("/auth/register", data={"email": "habit@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "habit@x.com", "password": "p"})
    client.post(
        "/log",
        data={
            "mood": "4",
            "activities": "walk, journaling",
            "sleep_hours": "7.5",
            "interaction_level": "3",
            "screen_time_hours": "3",
            "notes": "steady and clearer",
        },
    )

    r = client.post(
        "/api/habit/complete",
        json={
            "habit_key": "adaptive_reset",
            "habit_title": "Box Breath Reset",
            "emotional_state": "calm",
        },
    )
    data = json.loads(r.data)

    assert r.status_code == 200
    assert data["gamification"]["weekly_goal"]["current"] == 1
    assert data["gamification"]["total_points"] >= 15


def test_companion_prefers_llm_journal_and_live_music(client, monkeypatch):
    monkeypatch.setattr(
        companion_module,
        "analyze_journal_with_llm",
        lambda entries, user_message="": {
            "summary": "LLM summary",
            "patterns": ["Perfectionism"],
            "recurring_concerns": ["Sleep"],
            "emotional_insight": "You sound more reactive after poor sleep.",
            "prompt": "What would feeling 10 percent safer look like tonight?",
            "source": "openai:test-model",
        },
    )
    monkeypatch.setattr(
        companion_module,
        "fetch_spotify_recommendations",
        lambda query, limit=1: [
            {"title": "Live Spotify Pick", "url": "https://open.spotify.com/playlist/test", "source": "spotify"}
        ],
    )
    monkeypatch.setattr(
        companion_module,
        "fetch_youtube_recommendations",
        lambda query, limit=1: [
            {"title": "Live YouTube Pick", "url": "https://www.youtube.com/watch?v=test", "source": "youtube"}
        ],
    )

    client.post("/auth/register", data={"email": "live@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "live@x.com", "password": "p"})
    client.post(
        "/log",
        data={
            "mood": "3",
            "activities": "journaling, music",
            "sleep_hours": "6",
            "interaction_level": "2",
            "screen_time_hours": "4",
            "notes": "restless but trying",
        },
    )

    r = client.post("/api/companion/chat", json={"message": "help me reflect"})
    data = json.loads(r.data)

    assert r.status_code == 200
    assert data["journal"]["source"] == "openai:test-model"
    assert data["integrations"]["music_live"] is True
    assert data["music"][0]["spotify_url"] == "https://open.spotify.com/playlist/test"


def test_log_validation_surfaces_user_friendly_errors(client):
    client.post("/auth/register", data={"email": "invalid@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "invalid@x.com", "password": "p"})

    r = client.post(
        "/log",
        data={
            "mood": "9",
            "activities": "walk",
            "sleep_hours": "7",
            "interaction_level": "3",
            "screen_time_hours": "2",
            "notes": "steady",
        },
    )

    body = r.get_data(as_text=True)
    assert r.status_code == 400
    assert "between 1 and 5" in body


def test_dashboard_shows_weekly_reflection_and_state_explanations(client):
    client.post("/auth/register", data={"email": "reflect@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "reflect@x.com", "password": "p"})

    client.post(
        "/log",
        data={
            "mood": "2",
            "activities": "scrolling, alone",
            "sleep_hours": "5",
            "interaction_level": "1",
            "screen_time_hours": "9",
            "notes": "tired overwhelmed foggy",
        },
    )

    r = client.get("/dashboard")
    body = r.get_data(as_text=True)
    assert "Weekly Reflection" in body
    assert "Why This State?" in body


def test_user_can_edit_and_delete_entry(client):
    from sqlmodel import Session, select

    from app.models import Entry

    client.post("/auth/register", data={"email": "edit@x.com", "password": "p"})
    client.post("/auth/login", data={"email": "edit@x.com", "password": "p"})
    client.post(
        "/log",
        data={
            "mood": "3",
            "activities": "walk",
            "sleep_hours": "7",
            "interaction_level": "3",
            "screen_time_hours": "4",
            "notes": "steady",
        },
    )

    with Session(get_engine()) as session:
        entry = session.exec(select(Entry)).first()
        assert entry is not None
        entry_id = entry.id

    update = client.post(
        f"/entries/{entry_id}/edit",
        data={
            "mood": "5",
            "activities": "music, friends",
            "sleep_hours": "8",
            "interaction_level": "4",
            "screen_time_hours": "2",
            "notes": "good hopeful",
        },
        follow_redirects=True,
    )
    assert "Entry updated." in update.get_data(as_text=True)

    delete = client.post(f"/entries/{entry_id}/delete", follow_redirects=True)
    assert "Entry deleted." in delete.get_data(as_text=True)
