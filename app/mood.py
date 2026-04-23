import base64
import binascii
from collections import Counter
from datetime import date
from statistics import mean

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlmodel import Session, select

from .companion import build_companion_payload, build_gamification
from .database import get_engine
from .ml import DEFAULT_PREDICTED_MOOD, MIN_FORECAST_HISTORY, predict_next_mood
from .models import Entry, HabitEvent
from .opencv import detect_emotion

mood_bp = Blueprint("mood", __name__)

STATE_META = {
    "calm": {
        "label": "Calm",
        "palette": "calm",
        "description": "Balanced, settled, and emotionally steady.",
    },
    "energy": {
        "label": "Energy",
        "palette": "energy",
        "description": "Activated, social, and ready to move.",
    },
    "happiness": {
        "label": "Happiness",
        "palette": "happy",
        "description": "Light, upbeat, and emotionally open.",
    },
    "focus": {
        "label": "Focus",
        "palette": "focus",
        "description": "Clear, productive, and mentally engaged.",
    },
    "peace": {
        "label": "Peace",
        "palette": "peace",
        "description": "Rested, safe, and quietly content.",
    },
    "sad": {
        "label": "Sad",
        "palette": "sad",
        "description": "Emotionally low, reflective, and needing gentle support.",
    },
    "angry": {
        "label": "Angry",
        "palette": "angry",
        "description": "Activated, frustrated, and carrying sharp emotional charge.",
    },
    "gloomy": {
        "label": "Gloomy",
        "palette": "gloomy",
        "description": "Flat, drained, and muted by stress or emotional fog.",
    },
}

POSITIVE_SENTIMENT_TOKENS = {
    "good",
    "great",
    "calm",
    "better",
    "happy",
    "grateful",
    "clear",
    "focused",
    "hopeful",
    "rested",
    "peaceful",
}
NEGATIVE_SENTIMENT_TOKENS = {
    "sad",
    "angry",
    "tired",
    "overwhelmed",
    "stressed",
    "upset",
    "lonely",
    "drained",
    "bad",
    "frustrated",
    "anxious",
    "heavy",
    "foggy",
}


def _current_user_id() -> int:
    user_id = getattr(current_user, "id", None)
    if user_id is None:
        raise ValueError("Authenticated user is missing an id.")
    return int(user_id)


def _parse_optional_float(value: str) -> float | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    return float(cleaned)


def _parse_optional_int(value: str) -> int | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    return int(cleaned)


def _classify_emotion_state(
    mood: int,
    sleep_hours: float | None,
    interaction_level: int | None,
    screen_time_hours: float | None,
    activities: str,
    notes: str = "",
) -> str:
    activity_tokens = {
        token.strip().lower() for token in activities.split(",") if token.strip()
    }
    restorative = {
        "walk",
        "music",
        "meditation",
        "journaling",
        "reading",
        "nature",
        "yoga",
    }
    productive = {"study", "coding", "deep work", "reading", "planning", "writing"}
    social = {"friends", "family", "call", "meeting", "team", "hangout", "party"}

    sleep = sleep_hours or 0.0
    interaction = interaction_level or 3
    screen_time = screen_time_hours or 0.0
    sentiment = _sentiment_score(notes)

    if mood <= 2 and sentiment <= -2:
        return "sad"
    if mood <= 2 and (sleep <= 5.5 or screen_time >= 9):
        return "gloomy"
    if mood <= 3 and sentiment <= -3 and interaction <= 2:
        return "gloomy"
    if mood <= 2 and interaction >= 4 and activity_tokens & social:
        return "sad"
    if mood >= 3 and sentiment <= -2 and interaction >= 3 and screen_time >= 6:
        return "angry"
    if mood >= 4 and sentiment <= -1 and interaction >= 3:
        return "angry"

    if mood >= 5 or (mood >= 4 and interaction >= 4 and activity_tokens & social):
        return "happiness"
    if mood >= 4 and interaction >= 4:
        return "energy"
    if mood >= 3 and sleep >= 6 and (activity_tokens & productive) and screen_time <= 8:
        return "focus"
    if (
        mood >= 3
        and sleep >= 7.5
        and interaction <= 3
        and (activity_tokens & restorative)
    ):
        return "peace"
    return "calm"


def _sentiment_score(notes: str) -> int:
    tokens = [token.strip(".,!?;:").lower() for token in notes.split()]
    positives = sum(token in POSITIVE_SENTIMENT_TOKENS for token in tokens)
    negatives = sum(token in NEGATIVE_SENTIMENT_TOKENS for token in tokens)
    return positives - negatives


def _tokenize_activities(entries: list[Entry]) -> list[str]:
    tokens: list[str] = []
    for entry in entries:
        if not entry.activities:
            continue
        for raw_part in entry.activities.split(","):
            token = raw_part.strip().lower()
            if token:
                tokens.append(token)
    return tokens


def _state_payload(state_key: str) -> dict[str, str]:
    meta = STATE_META.get(state_key, STATE_META["calm"])
    return {
        "key": state_key,
        "label": meta["label"],
        "palette": meta["palette"],
        "description": meta["description"],
    }


def _load_user_entries(session: Session) -> list[Entry]:
    stmt = (
        select(Entry)
        .where(Entry.user_id == _current_user_id())
        .order_by(Entry.entry_date.asc(), Entry.created_at.asc(), Entry.id.asc())
    )
    return session.exec(stmt).all()


def _load_user_habit_events(session: Session) -> list[HabitEvent]:
    stmt = (
        select(HabitEvent)
        .where(HabitEvent.user_id == _current_user_id())
        .order_by(
            HabitEvent.occurred_on.asc(),
            HabitEvent.created_at.asc(),
            HabitEvent.id.asc(),
        )
    )
    return session.exec(stmt).all()


def _build_dashboard_summary(entries: list[Entry]) -> dict[str, object]:
    if not entries:
        return {
            "entry_count": 0,
            "average_mood": 0.0,
            "current_streak": 0,
            "trend_label": "Start logging to unlock your climate story.",
            "dominant_state": _state_payload("calm"),
            "top_activities": [],
            "average_sleep": 0.0,
            "average_interaction": 0.0,
            "state_breakdown": [],
            "realtime_suggestions": [
                "Add three entries with sleep and activity context to unlock more specific suggestions.",
                "Try a two-minute breathing reset to establish a calmer baseline.",
            ],
            "micro_activity": _build_micro_activity("calm"),
            "climate_note": (
                "Your dashboard will turn into a weekly reflection once you add a few entries."
            ),
            "latest_state_key": "calm",
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
        for name, count in Counter(_tokenize_activities(entries)).most_common(3)
    ]
    sleep_values = [
        entry.sleep_hours for entry in entries if entry.sleep_hours is not None
    ]
    interaction_values = [
        entry.interaction_level
        for entry in entries
        if entry.interaction_level is not None
    ]
    average_sleep = round(mean(sleep_values), 1) if sleep_values else 0.0
    average_interaction = (
        round(mean(interaction_values), 1) if interaction_values else 0.0
    )
    state_breakdown = [
        {
            **_state_payload(state_key),
            "count": count,
        }
        for state_key, count in state_counts.most_common()
    ]
    realtime_suggestions = _build_realtime_suggestions(
        dominant_state_key,
        average_sleep,
        average_interaction,
        top_activities,
        trend_label,
    )
    micro_activity = _build_micro_activity(dominant_state_key)

    note_parts = [
        f"Your average mood sits at {average_mood}/5, with the overall climate feeling {trend_label.lower()}.",
        f"The dominant emotional state this period is {_state_payload(dominant_state_key)['label'].lower()}.",
    ]
    if top_activities:
        spotlight = ", ".join(activity["name"] for activity in top_activities)
        note_parts.append(f"Your strongest anchors are {spotlight}.")
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
        note_parts.append(
            "A few more consistent check-ins will make the trend story even stronger."
        )

    return {
        "entry_count": len(entries),
        "average_mood": average_mood,
        "current_streak": current_streak if moods[-1] >= 4 else 0,
        "trend_label": trend_label,
        "dominant_state": _state_payload(dominant_state_key),
        "top_activities": top_activities,
        "average_sleep": average_sleep,
        "average_interaction": average_interaction,
        "state_breakdown": state_breakdown,
        "realtime_suggestions": realtime_suggestions,
        "micro_activity": micro_activity,
        "climate_note": " ".join(note_parts),
        "latest_state_key": entries[-1].emotion_state or dominant_state_key,
    }


def _build_realtime_suggestions(
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


def _build_micro_activity(state_key: str) -> dict[str, object]:
    activities = {
        "calm": {
            "title": "Box Breath Reset",
            "prompt": "Breathe in for 4, hold for 4, out for 4, hold for 4. Repeat four rounds.",
            "steps": ["Inhale 4", "Hold 4", "Exhale 4", "Hold 4"],
            "duration": 64,
            "button": "Start breathing cycle",
        },
        "energy": {
            "title": "Momentum Sprint",
            "prompt": "Use your current energy on one small win: tidy, stretch, or ship one unfinished task.",
            "steps": ["Pick one win", "Move for 30 sec", "Finish it", "Mark it done"],
            "duration": 90,
            "button": "Start sprint",
        },
        "happiness": {
            "title": "Amplify the Good",
            "prompt": "Lock in the high by naming one win, one person, and one moment worth remembering.",
            "steps": [
                "Name a win",
                "Name a person",
                "Name a moment",
                "Save it mentally",
            ],
            "duration": 75,
            "button": "Start gratitude loop",
        },
        "focus": {
            "title": "Two-Minute Focus Lock",
            "prompt": "Silence one distraction and commit to two minutes of deep attention on the next action.",
            "steps": [
                "Mute distraction",
                "Choose next action",
                "Work 120 sec",
                "Check progress",
            ],
            "duration": 120,
            "button": "Start focus timer",
        },
        "peace": {
            "title": "Gentle Reflection",
            "prompt": "Stay in the pocket. Breathe slowly and note what made today feel safe or clear.",
            "steps": [
                "Shoulders down",
                "Slow inhale",
                "Slow exhale",
                "Name one stabilizer",
            ],
            "duration": 80,
            "button": "Start reflection",
        },
        "sad": {
            "title": "Small Lift Challenge",
            "prompt": "Pick the smallest caring action available: water, sunlight, or one supportive message.",
            "steps": [
                "Stand up",
                "Drink water",
                "Message one person",
                "Take 5 slow breaths",
            ],
            "duration": 90,
            "button": "Start lift challenge",
        },
        "angry": {
            "title": "Decompression Drill",
            "prompt": "Release charge before reacting: unclench jaw, drop shoulders, breathe long on the exhale.",
            "steps": [
                "Unclench jaw",
                "Drop shoulders",
                "Exhale 6",
                "Delay reaction 2 min",
            ],
            "duration": 75,
            "button": "Start decompression",
        },
        "gloomy": {
            "title": "Fog Breaker",
            "prompt": "Beat the emotional fog with light motion and one concrete action you can finish fast.",
            "steps": [
                "Open blinds",
                "Walk 1 minute",
                "Pick one tiny task",
                "Finish it",
            ],
            "duration": 90,
            "button": "Start fog breaker",
        },
    }
    return activities.get(state_key, activities["calm"])


@mood_bp.route("/")
def index():
    return render_template("index.html")


@mood_bp.route("/log", methods=["GET", "POST"])
@login_required
def log():
    if request.method == "POST":
        mood_raw = request.form.get("mood", "").strip()
        activities = request.form.get("activities", "").strip()
        sleep_raw = request.form.get("sleep_hours", "")
        interaction_raw = request.form.get("interaction_level", "")
        screen_raw = request.form.get("screen_time_hours", "")
        notes = request.form.get("notes", "").strip()

        try:
            mood_value = int(mood_raw)
        except ValueError:
            flash("Emotional intensity must be a number from 1 to 5.", "warning")
            return render_template("log.html"), 400

        if not 1 <= mood_value <= 5:
            flash("Emotional intensity must be between 1 and 5.", "warning")
            return render_template("log.html"), 400

        try:
            sleep_hours = _parse_optional_float(sleep_raw)
            interaction_level = _parse_optional_int(interaction_raw)
            screen_time_hours = _parse_optional_float(screen_raw)
        except ValueError:
            flash(
                "Sleep, interaction, and screen time must be valid numbers.", "warning"
            )
            return render_template("log.html"), 400

        if sleep_hours is not None and not 0 <= sleep_hours <= 24:
            flash("Sleep hours must be between 0 and 24.", "warning")
            return render_template("log.html"), 400

        if interaction_level is not None and not 1 <= interaction_level <= 5:
            flash("Interaction level must be between 1 and 5.", "warning")
            return render_template("log.html"), 400

        if screen_time_hours is not None and not 0 <= screen_time_hours <= 24:
            flash("Screen time must be between 0 and 24 hours.", "warning")
            return render_template("log.html"), 400

        emotion_state = _classify_emotion_state(
            mood_value,
            sleep_hours,
            interaction_level,
            screen_time_hours,
            activities,
            notes,
        )

        entry = Entry(
            mood=mood_value,
            emotion_state=emotion_state,
            activities=activities or None,
            sleep_hours=sleep_hours,
            interaction_level=interaction_level,
            screen_time_hours=screen_time_hours,
            notes=notes or None,
            user_id=_current_user_id(),
        )
        with Session(get_engine()) as session:
            session.add(entry)
            session.commit()

        flash("Entry saved.", "success")
        return redirect(url_for("mood.dashboard"))

    return render_template("log.html")


@mood_bp.route("/dashboard")
@login_required
def dashboard():
    with Session(get_engine()) as session:
        entries = _load_user_entries(session)
        habit_events = _load_user_habit_events(session)

    data = [
        {
            "date": entry.entry_date.isoformat(),
            "mood": entry.mood,
            "state": _state_payload(entry.emotion_state or "calm"),
            "activities": entry.activities or "",
            "sleep_hours": entry.sleep_hours,
            "interaction_level": entry.interaction_level,
            "screen_time_hours": entry.screen_time_hours,
            "notes": entry.notes or "",
        }
        for entry in entries
    ]
    summary = _build_dashboard_summary(entries)
    companion = build_companion_payload(entries, habit_events)
    gamification = build_gamification(entries, habit_events)
    return render_template(
        "dashboard.html",
        entries=data,
        summary=summary,
        companion=companion,
        gamification=gamification,
    )


@mood_bp.route("/api/predict")
@login_required
def api_predict():
    with Session(get_engine()) as session:
        stmt = (
            select(Entry)
            .where(Entry.user_id == _current_user_id())
            .order_by(Entry.entry_date.desc(), Entry.created_at.desc(), Entry.id.desc())
            .limit(14)
        )
        recent_entries = list(reversed(list(session.exec(stmt).all())))
    recent = [entry.mood for entry in recent_entries]

    if len(recent) < MIN_FORECAST_HISTORY:
        fallback_state = recent_entries[-1].emotion_state if recent_entries else "calm"
        return jsonify(
            predicted_mood=DEFAULT_PREDICTED_MOOD,
            confidence=0.0,
            shap={},
            predicted_state=_state_payload(fallback_state),
        )

    pred, conf, shap = predict_next_mood(recent)
    reference_entry = recent_entries[-1]
    predicted_state = _classify_emotion_state(
        int(round(pred)),
        reference_entry.sleep_hours,
        reference_entry.interaction_level,
        reference_entry.screen_time_hours,
        reference_entry.activities or "",
        reference_entry.notes or "",
    )
    return jsonify(
        predicted_mood=round(pred, 2),
        confidence=round(conf, 2),
        shap=shap,
        predicted_state=_state_payload(predicted_state),
    )


@mood_bp.route("/api/capture", methods=["POST"])
@login_required
def api_capture():
    payload = request.get_json(silent=True)
    image_data = payload.get("image") if isinstance(payload, dict) else None
    if not image_data:
        return jsonify({"error": "no image supplied"}), 400

    try:
        encoded_part = image_data.split(",", 1)[1] if "," in image_data else image_data
        img_bytes = base64.b64decode(encoded_part, validate=True)
    except (ValueError, binascii.Error):
        return jsonify({"error": "invalid image payload"}), 400

    if not img_bytes:
        return jsonify({"error": "invalid image payload"}), 400

    result = detect_emotion(img_bytes)
    emotion_state = _classify_emotion_state(
        int(result["suggested_mood"]),
        None,
        None,
        None,
        "camera reflection",
    )

    entry = Entry(
        mood=int(result["suggested_mood"]),
        emotion_state=emotion_state,
        activities=None,
        notes=f"[Auto-detected] emotion={result['emotion']}",
        user_id=_current_user_id(),
    )
    with Session(get_engine()) as session:
        session.add(entry)
        session.commit()

    return jsonify(
        suggested_mood=int(result["suggested_mood"]),
        emotion=result["emotion"],
        confidence=round(float(result["confidence"]), 2),
        suggested_state=_state_payload(emotion_state),
    )


@mood_bp.route("/api/companion/chat", methods=["POST"])
@login_required
def api_companion_chat():
    payload = request.get_json(silent=True) or {}
    user_message = str(payload.get("message", "")).strip()

    with Session(get_engine()) as session:
        entries = _load_user_entries(session)
        habit_events = _load_user_habit_events(session)

    return jsonify(build_companion_payload(entries, habit_events, user_message=user_message))


@mood_bp.route("/api/habit/complete", methods=["POST"])
@login_required
def api_habit_complete():
    payload = request.get_json(silent=True) or {}
    habit_key = str(payload.get("habit_key", "adaptive_reset")).strip() or "adaptive_reset"
    habit_title = str(payload.get("habit_title", "Adaptive Reset")).strip() or "Adaptive Reset"
    emotional_state = str(payload.get("emotional_state", "calm")).strip() or "calm"

    if len(habit_key) > 80 or len(habit_title) > 120 or len(emotional_state) > 40:
        return jsonify({"error": "invalid habit payload"}), 400

    event = HabitEvent(
        occurred_on=date.today(),
        habit_key=habit_key,
        habit_title=habit_title,
        emotional_state=emotional_state,
        user_id=_current_user_id(),
    )
    with Session(get_engine()) as session:
        session.add(event)
        session.commit()
        entries = _load_user_entries(session)
        habit_events = _load_user_habit_events(session)

    return jsonify(
        {
            "message": "Habit completion saved.",
            "gamification": build_gamification(entries, habit_events),
        }
    )
