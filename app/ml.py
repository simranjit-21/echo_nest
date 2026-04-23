from pathlib import Path
from typing import Iterable

import numpy as np

MODEL_PATH = Path(__file__).parent.parent / "models" / "mood_lstm.pkl"
MIN_FORECAST_HISTORY = 5
DEFAULT_PREDICTED_MOOD = 3.0


class DummyMoodModel:
    """Fallback model that predicts from the recent average mood."""

    def predict(self, seq: np.ndarray) -> np.ndarray:
        if seq.ndim == 3:
            return np.mean(seq, axis=(1, 2), keepdims=True).reshape(seq.shape[0], 1)
        return np.array([[0.5]])


def _load_model():
    if not MODEL_PATH.exists():
        return DummyMoodModel()

    try:
        import joblib

        return joblib.load(MODEL_PATH)
    except Exception:
        return DummyMoodModel()


_model = _load_model()


def _scale(seq: Iterable[int]) -> np.ndarray:
    """Scale 1-5 moods to a 0-1 range."""
    arr = np.array(list(seq), dtype=float)
    if arr.size == 0:
        return arr
    return np.clip((arr - 1) / 4.0, 0.0, 1.0)


def predict_next_mood(recent_moods: list[int]) -> tuple[float, float, dict[str, float]]:
    """
    Return (predicted_mood, confidence, shap_dict).
    """
    if not recent_moods:
        return DEFAULT_PREDICTED_MOOD, 0.0, {}

    if len(recent_moods) < MIN_FORECAST_HISTORY:
        return float(recent_moods[-1]), 0.0, {}

    seq = _scale(recent_moods).reshape(1, -1, 1)

    try:
        prediction = np.asarray(_model.predict(seq), dtype=float).reshape(-1)
        pred_scaled = float(prediction[0]) if prediction.size else 0.5
    except Exception:
        pred_scaled = float(seq[0, -1, 0])

    pred = float(np.clip(pred_scaled * 4 + 1, 1.0, 5.0))
    confidence = float(np.clip(np.mean(np.abs(seq - seq.mean())), 0.0, 1.0))

    shap_dict: dict[str, float] = {}
    try:
        import shap

        explainer = shap.Explainer(_model)
        shap_vals = np.asarray(explainer(seq)[0].values).reshape(-1)
        feature_names = [f"t-{i}" for i in range(seq.shape[1])]
        shap_dict = {name: float(value) for name, value in zip(feature_names, shap_vals)}
    except Exception:
        pass

    return pred, confidence, shap_dict
