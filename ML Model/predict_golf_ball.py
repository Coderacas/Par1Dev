# =========================
# Cell 4: predict_golf_ball.py
# =========================

import pickle
import numpy as np
from features import validate_and_reshape

# ── Model path ────────────────────────────────────────────────────────────────
MODEL_PATH = "golf_ball_rf_model.pkl"


def _load_model(path: str = MODEL_PATH):
    """Loads the trained Random Forest model from a Pickle file."""
    with open(path, "rb") as f:
        return pickle.load(f)


# Load once at module import — avoids reloading on every call.
_model = _load_model(MODEL_PATH)


def predict_golf_ball_quality(features: np.ndarray) -> bool:
    """
    Predicts whether a golf ball is Good or Bad from its feature vector.

    Parameters
    ----------
    features : np.ndarray
        1-D array of N_FEATURES normalized values in range [0, 1].

    Returns
    -------
    bool
        True  → Good
        False → Bad
    """
    X = validate_and_reshape(features)          # validate + reshape to (1, N)
    prediction = _model.predict(X)[0]           # returns 0 or 1
    return bool(prediction)                     # 1 → True (Good), 0 → False (Bad)


# ── Usage example ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # Replace with real CV-extracted feature values
    sample_features = np.array([0.671, 0.064, 0.451, 0.824, 0.106,
                                 0.107, 0.797, 0.068, 0.100, 0.000])

    result = predict_golf_ball_quality(sample_features)

    print(f"Prediction : {result}")
    print(f"Ball status: {'Good ✔' if result else 'Bad ✘'}")
