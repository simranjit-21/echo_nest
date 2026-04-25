from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class StateSchema:
    key: str
    label: str
    palette: str
    description: str


@dataclass(frozen=True)
class PredictionResponse:
    predicted_mood: float
    confidence: float
    shap: dict[str, float]
    predicted_state: StateSchema

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CaptureResponse:
    suggested_mood: int
    emotion: str
    confidence: float
    suggested_state: StateSchema

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HabitCompletionResponse:
    message: str
    gamification: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
