import base64
import binascii
from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlmodel import Session, select

from .companion import build_companion_payload, build_gamification
from .database import get_engine
from .ml import DEFAULT_PREDICTED_MOOD, MIN_FORECAST_HISTORY, predict_next_mood
from .models import Entry, HabitEvent
from .opencv import detect_emotion
from .schemas import CaptureResponse, HabitCompletionResponse, PredictionResponse, StateSchema
from .services.dashboard import build_dashboard_summary
from .services.emotion import (
    classify_emotion_state,
    explain_emotion_state,
    state_payload,
)
from .services.validation import ValidationError, validate_entry_form

mood_bp = Blueprint("mood", __name__)


def _current_user_id() -> int:
    user_id = getattr(current_user, "id", None)
    if user_id is None:
        raise ValueError("Authenticated user is missing an id.")
    return int(user_id)


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


def _load_entry_or_404(session: Session, entry_id: int) -> Entry | None:
    entry = session.get(Entry, entry_id)
    if entry is None or entry.user_id != _current_user_id():
        return None
    return entry


def _serialize_entry(entry: Entry) -> dict[str, object]:
    explanation = explain_emotion_state(
        entry.mood,
        entry.sleep_hours,
        entry.interaction_level,
        entry.screen_time_hours,
        entry.activities or "",
        entry.notes or "",
    )
    return {
        "id": entry.id,
        "date": entry.entry_date.isoformat(),
        "mood": entry.mood,
        "state": state_payload(entry.emotion_state or "calm"),
        "activities": entry.activities or "",
        "sleep_hours": entry.sleep_hours,
        "interaction_level": entry.interaction_level,
        "screen_time_hours": entry.screen_time_hours,
        "notes": entry.notes or "",
        "explanation": {
            "reasons": explanation.reasons,
            "signals": explanation.signals,
        },
    }


def _entry_form_defaults(entry: Entry | None = None) -> dict[str, object]:
    return {
        "mood": entry.mood if entry else "",
        "activities": entry.activities or "" if entry else "",
        "sleep_hours": entry.sleep_hours if entry and entry.sleep_hours is not None else "",
        "interaction_level": (
            entry.interaction_level
            if entry and entry.interaction_level is not None
            else ""
        ),
        "screen_time_hours": (
            entry.screen_time_hours
            if entry and entry.screen_time_hours is not None
            else ""
        ),
        "notes": entry.notes or "" if entry else "",
    }


@mood_bp.route("/")
def index():
    return render_template("index.html")


@mood_bp.route("/log", methods=["GET", "POST"])
@login_required
def log():
    form_values = _entry_form_defaults()
    if request.method == "POST":
        form_values = {key: request.form.get(key, "") for key in form_values}
        try:
            form_data = validate_entry_form(request.form)
        except ValidationError as exc:
            flash(str(exc), "warning")
            return render_template(
                "log.html",
                form_values=form_values,
                mode="create",
            ), 400

        explanation = explain_emotion_state(
            form_data.mood,
            form_data.sleep_hours,
            form_data.interaction_level,
            form_data.screen_time_hours,
            form_data.activities,
            form_data.notes,
        )
        entry = Entry(
            mood=form_data.mood,
            emotion_state=explanation.state_key,
            activities=form_data.activities or None,
            sleep_hours=form_data.sleep_hours,
            interaction_level=form_data.interaction_level,
            screen_time_hours=form_data.screen_time_hours,
            notes=form_data.notes or None,
            user_id=_current_user_id(),
        )
        with Session(get_engine()) as session:
            session.add(entry)
            session.commit()

        flash("Entry saved.", "success")
        return redirect(url_for("mood.dashboard"))

    return render_template("log.html", form_values=form_values, mode="create")


@mood_bp.route("/entries/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_entry(entry_id: int):
    with Session(get_engine()) as session:
        entry = _load_entry_or_404(session, entry_id)
        if entry is None:
            flash("Entry not found.", "warning")
            return redirect(url_for("mood.dashboard"))

        form_values = _entry_form_defaults(entry)
        if request.method == "POST":
            form_values = {key: request.form.get(key, "") for key in form_values}
            try:
                form_data = validate_entry_form(request.form)
            except ValidationError as exc:
                flash(str(exc), "warning")
                return render_template(
                    "log.html",
                    form_values=form_values,
                    mode="edit",
                    entry=entry,
                ), 400

            explanation = explain_emotion_state(
                form_data.mood,
                form_data.sleep_hours,
                form_data.interaction_level,
                form_data.screen_time_hours,
                form_data.activities,
                form_data.notes,
            )
            entry.mood = form_data.mood
            entry.emotion_state = explanation.state_key
            entry.activities = form_data.activities or None
            entry.sleep_hours = form_data.sleep_hours
            entry.interaction_level = form_data.interaction_level
            entry.screen_time_hours = form_data.screen_time_hours
            entry.notes = form_data.notes or None
            session.add(entry)
            session.commit()

            flash("Entry updated.", "success")
            return redirect(url_for("mood.dashboard"))

    return render_template("log.html", form_values=form_values, mode="edit", entry=entry)


@mood_bp.route("/entries/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id: int):
    with Session(get_engine()) as session:
        entry = _load_entry_or_404(session, entry_id)
        if entry is None:
            flash("Entry not found.", "warning")
        else:
            session.delete(entry)
            session.commit()
            flash("Entry deleted.", "info")
    return redirect(url_for("mood.dashboard"))


@mood_bp.route("/dashboard")
@login_required
def dashboard():
    return _render_dashboard()


def _render_dashboard(user_message: str = ""):
    with Session(get_engine()) as session:
        entries = _load_user_entries(session)
        habit_events = _load_user_habit_events(session)

    serialized_entries = [_serialize_entry(entry) for entry in entries]
    summary = build_dashboard_summary(entries)
    companion = build_companion_payload(entries, habit_events, user_message=user_message)
    gamification = build_gamification(entries, habit_events)
    recent_entries = list(reversed(serialized_entries[-5:]))
    return render_template(
        "dashboard.html",
        entries=serialized_entries,
        recent_entries=recent_entries,
        summary=summary,
        companion=companion,
        gamification=gamification,
        companion_message=user_message,
    )


@mood_bp.route("/dashboard/companion", methods=["POST"])
@login_required
def dashboard_companion():
    user_message = str(request.form.get("message", "")).strip()
    return _render_dashboard(user_message=user_message)


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
        fallback = state_payload(fallback_state)
        return jsonify(
            PredictionResponse(
                predicted_mood=DEFAULT_PREDICTED_MOOD,
                confidence=0.0,
                shap={},
                predicted_state=StateSchema(**fallback),
            ).to_dict()
        )

    pred, conf, shap = predict_next_mood(recent)
    reference_entry = recent_entries[-1]
    predicted_state = classify_emotion_state(
        int(round(pred)),
        reference_entry.sleep_hours,
        reference_entry.interaction_level,
        reference_entry.screen_time_hours,
        reference_entry.activities or "",
        reference_entry.notes or "",
    )
    payload = state_payload(predicted_state)
    return jsonify(
        PredictionResponse(
            predicted_mood=round(pred, 2),
            confidence=round(conf, 2),
            shap=shap,
            predicted_state=StateSchema(**payload),
        ).to_dict()
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
    emotion_state = classify_emotion_state(
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

    payload = state_payload(emotion_state)
    return jsonify(
        CaptureResponse(
            suggested_mood=int(result["suggested_mood"]),
            emotion=result["emotion"],
            confidence=round(float(result["confidence"]), 2),
            suggested_state=StateSchema(**payload),
        ).to_dict()
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
        HabitCompletionResponse(
            message="Habit completion saved.",
            gamification=build_gamification(entries, habit_events),
        ).to_dict()
    )
