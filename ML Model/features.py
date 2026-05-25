# =========================
# Cell 1: features.py
# =========================

import numpy as np

# ── Feature definitions ───────────────────────────────────────────────────────
# Modify this list to match your actual extracted CV features.
# Order must match the order of values in the input array.
FEATURE_NAMES = [
    "feature_0",   # e.g. circularity
    "feature_1",   # e.g. brightness_mean
    "feature_2",   # e.g. contrast_ratio
    "feature_3",   # e.g. edge_density
    "feature_4",   # e.g. texture_uniformity
    "feature_5",   # e.g. crack_ratio
    "feature_6",   # e.g. roundness
    "feature_7",   # e.g. surface_roughness
    "feature_8",   # e.g. stain_coverage
    "feature_9",   # e.g. deformation_index
]

N_FEATURES = len(FEATURE_NAMES)


def validate_and_reshape(features: np.ndarray) -> np.ndarray:
    """
    Validates a 1-D feature array and reshapes it for scikit-learn input.

    Parameters
    ----------
    features : np.ndarray
        1-D array of normalized feature values in range [0, 1].

    Returns
    -------
    np.ndarray
        2-D array of shape (1, N_FEATURES) ready for sklearn .predict().

    Raises
    ------
    TypeError  : if input is not a NumPy array or contains non-numeric values.
    ValueError : if feature count mismatches or values are outside [0, 1].
    """

    # ── Type check ────────────────────────────────────────────────────────────
    if not isinstance(features, np.ndarray):
        raise TypeError(f"Input must be a NumPy array, got {type(features)}.")

    if not np.issubdtype(features.dtype, np.number):
        raise TypeError(f"Array must contain numeric values, got dtype={features.dtype}.")

    # ── Flatten to 1-D in case a 2-D row is passed ───────────────────────────
    features = features.flatten()

    # ── Feature count check ───────────────────────────────────────────────────
    if features.shape[0] != N_FEATURES:
        raise ValueError(
            f"Expected {N_FEATURES} features ({FEATURE_NAMES}), "
            f"but got {features.shape[0]}."
        )

    # ── Range check [0, 1] ────────────────────────────────────────────────────
    if np.any(features < 0.0) or np.any(features > 1.0):
        out_of_range = {
            FEATURE_NAMES[i]: features[i]
            for i in range(N_FEATURES)
            if not (0.0 <= features[i] <= 1.0)
        }
        raise ValueError(f"Feature values must be in [0, 1]. Out-of-range: {out_of_range}")

    # ── Reshape to (1, N_FEATURES) for sklearn ────────────────────────────────
    return features.reshape(1, -1)
