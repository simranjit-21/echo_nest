from __future__ import annotations

from dataclasses import dataclass


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class EntryFormData:
    mood: int
    activities: str
    sleep_hours: float | None
    interaction_level: int | None
    screen_time_hours: float | None
    notes: str


def _parse_optional_float(value: str, *, label: str) -> float | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValidationError(f"{label} must be a valid number.") from exc


def _parse_optional_int(value: str, *, label: str) -> int | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ValidationError(f"{label} must be a whole number.") from exc


def validate_entry_form(form: object) -> EntryFormData:
    mood_raw = str(form.get("mood", "")).strip()
    activities = str(form.get("activities", "")).strip()
    notes = str(form.get("notes", "")).strip()

    try:
        mood = int(mood_raw)
    except ValueError as exc:
        raise ValidationError("Emotional intensity must be a number from 1 to 5.") from exc

    if not 1 <= mood <= 5:
        raise ValidationError("Emotional intensity must be between 1 and 5.")

    sleep_hours = _parse_optional_float(str(form.get("sleep_hours", "")), label="Sleep hours")
    interaction_level = _parse_optional_int(
        str(form.get("interaction_level", "")), label="Interaction level"
    )
    screen_time_hours = _parse_optional_float(
        str(form.get("screen_time_hours", "")), label="Screen time"
    )

    if sleep_hours is not None and not 0 <= sleep_hours <= 24:
        raise ValidationError("Sleep hours must be between 0 and 24.")
    if interaction_level is not None and not 1 <= interaction_level <= 5:
        raise ValidationError("Interaction level must be between 1 and 5.")
    if screen_time_hours is not None and not 0 <= screen_time_hours <= 24:
        raise ValidationError("Screen time must be between 0 and 24 hours.")
    if len(activities) > 280:
        raise ValidationError("Activities should stay under 280 characters.")
    if len(notes) > 2000:
        raise ValidationError("Notes should stay under 2000 characters.")

    return EntryFormData(
        mood=mood,
        activities=activities,
        sleep_hours=sleep_hours,
        interaction_level=interaction_level,
        screen_time_hours=screen_time_hours,
        notes=notes,
    )
