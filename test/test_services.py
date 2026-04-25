from app.models import Entry
from app.env import load_dotenv
from app.services.dashboard import build_dashboard_summary
from app.services.emotion import explain_emotion_state, sentiment_score
from app.services.validation import ValidationError, validate_entry_form


def test_sentiment_score_tracks_positive_and_negative_tokens():
    assert sentiment_score("hopeful calm grateful") > 0
    assert sentiment_score("overwhelmed tired foggy") < 0


def test_explain_emotion_state_returns_state_and_reasons():
    explanation = explain_emotion_state(
        mood=2,
        sleep_hours=4.5,
        interaction_level=1,
        screen_time_hours=10,
        activities="scrolling, alone",
        notes="tired overwhelmed drained foggy",
    )

    assert explanation.state_key in {"gloomy", "sad"}
    assert explanation.reasons
    assert explanation.signals["sentiment_score"] < 0


def test_validate_entry_form_rejects_invalid_values():
    bad_form = {
        "mood": "7",
        "activities": "walk",
        "sleep_hours": "8",
        "interaction_level": "3",
        "screen_time_hours": "2",
        "notes": "steady",
    }

    try:
        validate_entry_form(bad_form)
    except ValidationError as exc:
        assert "between 1 and 5" in str(exc)
    else:
        raise AssertionError("Expected validation error for invalid mood.")


def test_build_dashboard_summary_includes_weekly_reflection():
    entries = [
        Entry(
            mood=4,
            emotion_state="focus",
            activities="reading, deep work",
            sleep_hours=7.5,
            interaction_level=2,
            screen_time_hours=4,
            user_id=1,
        ),
        Entry(
            mood=5,
            emotion_state="happiness",
            activities="walk, music",
            sleep_hours=8,
            interaction_level=4,
            screen_time_hours=3,
            user_id=1,
        ),
        Entry(
            mood=4,
            emotion_state="peace",
            activities="reading, journaling",
            sleep_hours=7,
            interaction_level=2,
            screen_time_hours=2,
            user_id=1,
        ),
    ]

    summary = build_dashboard_summary(entries)

    assert "weekly_reflection" in summary
    assert summary["weekly_reflection"]["headline"]
    assert summary["micro_activity"]["title"]
    assert summary["historical_analytics"]["headline"]


def test_load_dotenv_reads_values_without_overwriting_existing(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("SECRET_KEY=from-file\nLOG_LEVEL=DEBUG\n", encoding="utf-8")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    load_dotenv(dotenv)

    import os

    assert os.environ["SECRET_KEY"] == "from-file"
    assert os.environ["LOG_LEVEL"] == "INFO"
