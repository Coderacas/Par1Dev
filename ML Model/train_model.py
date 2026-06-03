from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit, cross_val_predict, cross_val_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "PythonDev" / "Project" / "PrototypeDev" / "data" / "features_dataset_ml.csv"
MODEL_PATH = PROJECT_ROOT / "golf_ball_rf_model.pkl"
MODEL_COPY_PATH = PROJECT_ROOT / "ML Model" / "golf_ball_rf_model.pkl"

LABEL_TO_ID = {
    "mala": 0,
    "buena": 1,
}

METADATA_COLUMNS = {
    "timestamp",
    "sample_id",
    "label",
    "estacion",
    "roi_x",
    "roi_y",
    "roi_w",
    "roi_h",
}

RF_PARAMS = {
    "n_estimators": 400,
    "max_depth": None,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "class_weight": {0: 6, 1: 1},
    "random_state": 42,
    "n_jobs": -1,
}


def load_dataset(dataset_path: Path = DATASET_PATH):
    if not dataset_path.exists():
        raise FileNotFoundError(f"No existe el dataset: {dataset_path}")

    df = pd.read_csv(dataset_path)
    df = df[df["label"].isin(LABEL_TO_ID)].copy()

    if df.empty:
        raise ValueError("El dataset no tiene filas con labels 'buena'/'mala'.")

    feature_columns = [
        col
        for col in df.columns
        if col not in METADATA_COLUMNS and pd.api.types.is_numeric_dtype(df[col])
    ]

    if not feature_columns:
        raise ValueError("No encontre columnas numericas de features.")

    X = df[feature_columns].astype(np.float32)
    y = df["label"].map(LABEL_TO_ID).astype(int)

    return df, X, y, feature_columns


def train():
    df, X, y, feature_columns = load_dataset()

    print(f"Dataset: {DATASET_PATH}")
    print(f"Filas: {len(df)}")
    print("Labels:")
    print(df["label"].value_counts())
    print()
    print(f"Features usadas: {len(feature_columns)}")

    splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y))
    X_np = X.to_numpy(dtype=np.float32)
    y_np = y.to_numpy(dtype=int)
    X_train, X_test = X_np[train_idx], X_np[test_idx]
    y_train, y_test = y_np[train_idx], y_np[test_idx]

    clf = RandomForestClassifier(**RF_PARAMS)

    print("\nEntrenando RandomForest...")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print("\nHoldout test")
    print(f"Accuracy: {accuracy:.4f}")
    print("Classification report:")
    print(classification_report(y_test, y_pred, target_names=["mala", "buena"], zero_division=0))
    print("Confusion matrix (rows=real, cols=pred):")
    print(confusion_matrix(y_test, y_pred, labels=[0, 1]))

    min_class_count = int(y.value_counts().min())
    cv_splits = max(2, min(5, min_class_count))
    cv_model = RandomForestClassifier(**RF_PARAMS)
    cv_scores = cross_val_score(cv_model, X_np, y_np, cv=cv_splits, scoring="balanced_accuracy")
    print(f"\nCV balanced accuracy ({cv_splits} folds): {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")

    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    cv_proba_good = cross_val_predict(
        RandomForestClassifier(**RF_PARAMS),
        X_np,
        y_np,
        cv=cv,
        method="predict_proba",
    )[:, 1]

    best_threshold = 0.50
    best_balanced_accuracy = -1.0
    best_confusion = None

    for threshold in np.linspace(0.10, 0.95, 18):
        y_pred_threshold = (cv_proba_good >= threshold).astype(int)
        score = balanced_accuracy_score(y_np, y_pred_threshold)

        if score > best_balanced_accuracy:
            best_balanced_accuracy = score
            best_threshold = float(threshold)
            best_confusion = confusion_matrix(y, y_pred_threshold, labels=[0, 1])

    print("\nUmbral calibrado con cross-validation")
    print(f"Probabilidad minima para BUENA: {best_threshold:.2f}")
    print(f"Balanced accuracy con umbral: {best_balanced_accuracy:.4f}")
    print("Confusion matrix CV con umbral (rows=real, cols=pred):")
    print(best_confusion)

    final_model = RandomForestClassifier(**RF_PARAMS)
    final_model.fit(X_np, y_np)

    bundle = {
        "model": final_model,
        "feature_columns": feature_columns,
        "label_to_id": LABEL_TO_ID,
        "id_to_label": {v: k for k, v in LABEL_TO_ID.items()},
        "good_probability_threshold": best_threshold,
        "dataset_path": str(DATASET_PATH),
        "rf_params": RF_PARAMS,
    }

    joblib.dump(bundle, MODEL_PATH)
    joblib.dump(bundle, MODEL_COPY_PATH)

    importances = final_model.feature_importances_
    ranked = sorted(zip(feature_columns, importances), key=lambda item: item[1], reverse=True)

    print("\nTop feature importances:")
    for name, importance in ranked[:15]:
        print(f"  {name:<28} {importance:.4f}")

    print(f"\nModelo guardado en: {MODEL_PATH}")
    print(f"Copia guardada en: {MODEL_COPY_PATH}")

    return bundle


if __name__ == "__main__":
    train()
