"""
Diagnostic Agent
----------------
Loads the custom-trained CNN (.keras) and predicts the Kellgren-Lawrence (KL)
severity grade (0-4) from a preprocessed knee X-ray.

KL Grading Scale:
  0 — None:      No radiographic features of OA
  1 — Doubtful:  Minute osteophytes, doubtful significance
  2 — Minimal:   Definite osteophytes, possible joint-space narrowing
  3 — Moderate:  Moderate osteophytes, definite narrowing, some sclerosis
  4 — Severe:    Large osteophytes, marked narrowing, severe sclerosis
"""

import os
import numpy as np
import tensorflow as tf
from typing import Tuple

from app.services.image_processor import preprocess_xray

# ── Model Configuration ──────────────────────────────────────────────────────
MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "ml_assets", "cnn_weights", "CNN.keras"
)

# Human-readable labels for each KL grade
KL_LABELS = {
    0: "Grade 0 — Normal: No radiographic features of osteoarthritis.",
    1: "Grade 1 — Doubtful: Minute osteophytes of doubtful significance.",
    2: "Grade 2 — Minimal: Definite osteophytes with possible joint-space narrowing.",
    3: "Grade 3 — Moderate: Moderate osteophytes, definite joint-space narrowing, some sclerosis.",
    4: "Grade 4 — Severe: Large osteophytes, marked joint-space narrowing, severe sclerosis and bone deformity.",
}

# ── Singleton Model Loader ───────────────────────────────────────────────────
_model = None


def _load_model() -> tf.keras.Model:
    """
    Lazy-load the CNN model on first call and cache it as a module-level
    singleton so we don't reload weights on every request.
    """
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"CNN weights not found at {MODEL_PATH}. "
                "Ensure CNN.keras is placed in app/ml_assets/cnn_weights/"
            )
        _model = tf.keras.models.load_model(MODEL_PATH)
    return _model


def predict_kl_grade(image_bytes: bytes) -> Tuple[int, float, str]:
    """
    Run the full diagnostic pipeline on raw X-ray bytes.

    Steps:
      1. Preprocess the image (grayscale, ROI, resize, normalise)
      2. Feed into the CNN
      3. Extract the predicted KL grade and confidence

    Args:
        image_bytes: Raw image file bytes.

    Returns:
        Tuple of (kl_grade, confidence, diagnosis_summary)
          - kl_grade:          int 0-4
          - confidence:        float 0.0-1.0 (softmax probability of predicted class)
          - diagnosis_summary: Human-readable description of the grade
    """
    model = _load_model()

    # Preprocess → (1, 256, 256, 1)
    processed = preprocess_xray(image_bytes)

    # Inference
    predictions = model.predict(processed, verbose=0)  # shape: (1, 5)

    # Extract results
    kl_grade = int(np.argmax(predictions[0]))
    confidence = float(np.max(predictions[0]))
    diagnosis_summary = KL_LABELS.get(kl_grade, "Unknown grade")

    return kl_grade, confidence, diagnosis_summary


def get_model_info() -> dict:
    """Return basic metadata about the loaded CNN (useful for health checks)."""
    model = _load_model()
    return {
        "model_name": model.name,
        "input_shape": str(model.input_shape),
        "output_shape": str(model.output_shape),
        "total_params": int(model.count_params()),
    }
