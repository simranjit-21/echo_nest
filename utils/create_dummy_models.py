# utils/create_dummy_models.py
import pickle
import numpy as np
from pathlib import Path

# Create a simple dummy LSTM-like model that just returns average of input
# This is a placeholder so the app can run without trained models

class DummyMoodModel:
    """Dummy model that predicts based on recent average mood."""
    
    def predict(self, seq):
        # seq shape: (batch, seq_len, 1) - scaled 0-1 values
        # Return average as prediction
        if seq.ndim == 3:
            return np.mean(seq, axis=(1, 2), keepdims=True).reshape(seq.shape[0], 1)
        return np.array([0.5])

models_dir = Path(__file__).parent.parent / "models"
models_dir.mkdir(exist_ok=True)

# Save dummy model
dummy_model = DummyMoodModel()
with open(models_dir / "mood_lstm.pkl", "wb") as f:
    pickle.dump(dummy_model, f)

print("Created dummy mood_lstm.pkl model")

# Create a dummy emotion CNN model placeholder
print("Note: emotion_cnn.pt needs PyTorch model - will use fallback in opencv.py")
