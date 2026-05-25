# =========================
# Cell 2: dataset_generation.py
# =========================

import numpy as np
from sklearn.model_selection import train_test_split
from features import N_FEATURES, FEATURE_NAMES

# ── Reproducibility ───────────────────────────────────────────────────────────
RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

# ── Dataset size ──────────────────────────────────────────────────────────────
N_SAMPLES = 500


def generate_synthetic_dataset():
    """
    Generates a synthetic dataset of golf ball feature vectors with binary labels.

    Returns
    -------
    X : np.ndarray of shape (N_SAMPLES, N_FEATURES)  — feature matrix
    y : np.ndarray of shape (N_SAMPLES,)              — labels (1=Good, 0=Bad)
    """

    # ── Generate random feature values in [0, 1] ─────────────────────────────
    X = rng.uniform(low=0.0, high=1.0, size=(N_SAMPLES, N_FEATURES))

    # ── PLACEHOLDER LABEL LOGIC ───────────────────────────────────────────────
    # TODO: Replace this synthetic rule with REAL labeled inspection data.
    #       This heuristic is only used to generate a working training dataset.
    #
    # Current rule (example only):
    #   A ball is "Good" (1) if the mean of all its features > 0.5
    #   Otherwise it is "Bad" (0)
    # ─────────────────────────────────────────────────────────────────────────
    y = (X.mean(axis=1) > 0.5).astype(int)

    print(f"Dataset generated: {N_SAMPLES} samples, {N_FEATURES} features")
    print(f"  Good (1): {y.sum()}  |  Bad (0): {(y == 0).sum()}")
    print(f"  Features: {FEATURE_NAMES}\n")

    return X, y


def split_dataset(X: np.ndarray, y: np.ndarray):
    """
    Splits the dataset into training and test sets (80/20).

    Returns
    -------
    X_train, X_test, y_train, y_test
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=RANDOM_SEED,
        stratify=y        # preserves class ratio in both splits
    )

    print(f"Train set: {X_train.shape[0]} samples")
    print(f"Test  set: {X_test.shape[0]} samples\n")

    return X_train, X_test, y_train, y_test


# ── Run standalone ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    X, y = generate_synthetic_dataset()
    X_train, X_test, y_train, y_test = split_dataset(X, y)
