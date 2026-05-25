# =========================
# Cell 3: train_model.py
# =========================

import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from dataset_generation import generate_synthetic_dataset, split_dataset

# ── Output path ───────────────────────────────────────────────────────────────
MODEL_PATH = "golf_ball_rf_model.pkl"

# ── Hyperparameters ───────────────────────────────────────────────────────────
# Adjust these to tune the model once real data is available.
RF_PARAMS = {
    "n_estimators": 200,       # number of trees
    "max_depth": None,         # grow full trees; set int to limit
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "class_weight": "balanced", # handles class imbalance automatically
    "random_state": 42,
    "n_jobs": -1,              # use all CPU cores
}


def train():
    # ── 1. Load data ─────────────────────────────────────────────────────────
    X, y = generate_synthetic_dataset()
    X_train, X_test, y_train, y_test = split_dataset(X, y)

    # ── 2. Instantiate and train classifier ───────────────────────────────────
    print("Training Random Forest classifier...")
    clf = RandomForestClassifier(**RF_PARAMS)
    clf.fit(X_train, y_train)
    print("Training complete.\n")

    # ── 3. Evaluate on test set ───────────────────────────────────────────────
    y_pred = clf.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy : {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Bad (0)", "Good (1)"]))
    print("Confusion Matrix (rows=actual, cols=predicted):")
    print(confusion_matrix(y_test, y_pred))
    print()

    # ── 4. Feature importances (useful for future feature selection) ──────────
    from features import FEATURE_NAMES
    importances = clf.feature_importances_
    ranked = sorted(zip(FEATURE_NAMES, importances), key=lambda x: x[1], reverse=True)
    print("Feature importances (ranked):")
    for name, imp in ranked:
        print(f"  {name:<25} {imp:.4f}")
    print()

    # ── 5. Save model to Pickle ───────────────────────────────────────────────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    print(f"Model saved → {MODEL_PATH}")

    return clf


# ── Run standalone ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    train()
