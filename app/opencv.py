from pathlib import Path

import cv2
import numpy as np
import torch

MODEL_PATH = Path(__file__).parent.parent / "models" / "emotion_cnn.pt"
DEFAULT_EMOTION_RESULT = {
    "emotion": "neutral",
    "confidence": 0.0,
    "suggested_mood": 3,
}

EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
EMOTION_TO_MOOD = {
    "happy": 5,
    "surprise": 5,
    "neutral": 3,
    "sad": 2,
    "fear": 2,
    "disgust": 2,
    "angry": 1,
}


def _load_emotion_model():
    if not MODEL_PATH.exists():
        return None

    try:
        model = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        model.eval()
        return model
    except Exception:
        return None


_emotion_model = _load_emotion_model()


def _preprocess(face_img: np.ndarray) -> torch.Tensor:
    """Resize, normalize, and convert an image into a model-ready tensor."""
    img = cv2.resize(face_img, (64, 64))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(img).float() / 255.0
    return tensor.permute(2, 0, 1).unsqueeze(0)


def detect_emotion(image_bytes: bytes) -> dict[str, float | int | str]:
    if _emotion_model is None or not image_bytes:
        return DEFAULT_EMOTION_RESULT.copy()

    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        return DEFAULT_EMOTION_RESULT.copy()

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )

    if len(faces) == 0:
        return DEFAULT_EMOTION_RESULT.copy()

    x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
    face_roi = img[y : y + h, x : x + w]

    try:
        tensor = _preprocess(face_roi)
        with torch.no_grad():
            logits = _emotion_model(tensor)
            probs = torch.nn.functional.softmax(logits, dim=1).squeeze()
            conf, idx = torch.max(probs, dim=0)

        emotion = EMOTION_LABELS[int(idx)]
        suggested = EMOTION_TO_MOOD.get(emotion, 3)
        return {
            "emotion": emotion,
            "confidence": float(conf),
            "suggested_mood": int(suggested),
        }
    except Exception:
        return DEFAULT_EMOTION_RESULT.copy()
