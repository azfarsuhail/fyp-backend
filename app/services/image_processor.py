"""
Image Processor Service
-----------------------
Handles all preprocessing required before feeding a knee X-ray into the CNN:
  1. Load raw image bytes
  2. Convert to grayscale
  3. Resize to 256×256
  4. Extract Region of Interest (ROI) — centre-crop to focus on the knee joint
  5. Normalize pixel values to [0, 1]
  6. Return a NumPy array shaped (1, 256, 256, 1) ready for model.predict()
"""

import io
import numpy as np
from PIL import Image, ImageFilter

# ── Constants ─────────────────────────────────────────────────────────────────
TARGET_SIZE = (256, 256)  # Must match CNN input shape


def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    """Open raw bytes as a PIL Image."""
    return Image.open(io.BytesIO(image_bytes))


def convert_to_grayscale(img: Image.Image) -> Image.Image:
    """Convert any image to single-channel grayscale."""
    return img.convert("L")


def resize_image(img: Image.Image, size: tuple = TARGET_SIZE) -> Image.Image:
    """Resize image to the target dimensions using high-quality Lanczos resampling."""
    return img.resize(size, Image.Resampling.LANCZOS)


def extract_roi(img: Image.Image, margin_ratio: float = 0.1) -> Image.Image:
    """
    Extract the Region of Interest by centre-cropping.

    For knee X-rays the joint space is typically near the centre of the image.
    We crop away a configurable margin from each edge to remove irrelevant
    anatomy and imaging artefacts (e.g. lead markers, borders).

    Args:
        img: Input PIL Image (any size).
        margin_ratio: Fraction of each dimension to remove from each side.
                      0.1 means 10 % is trimmed from left, right, top, bottom.

    Returns:
        Cropped PIL Image focused on the knee joint area.
    """
    w, h = img.size
    left = int(w * margin_ratio)
    top = int(h * margin_ratio)
    right = int(w * (1 - margin_ratio))
    bottom = int(h * (1 - margin_ratio))
    return img.crop((left, top, right, bottom))


def apply_clahe_enhancement(img: Image.Image) -> Image.Image:
    """
    Apply contrast enhancement to improve visibility of joint features.
    Uses PIL's autocontrast as a lightweight CLAHE alternative.
    """
    from PIL import ImageOps
    return ImageOps.autocontrast(img, cutoff=1)


def image_to_array(img: Image.Image) -> np.ndarray:
    """
    Convert a grayscale PIL Image to a normalised NumPy array
    shaped (1, 256, 256, 1) — ready for TensorFlow model.predict().
    """
    arr = np.array(img, dtype=np.float32) / 255.0   # Normalise to [0, 1]
    arr = arr.reshape(1, TARGET_SIZE[0], TARGET_SIZE[1], 1)  # Batch + channel dims
    return arr


def preprocess_xray(image_bytes: bytes) -> np.ndarray:
    """
    Full preprocessing pipeline: bytes → model-ready NumPy array.

    Pipeline steps:
      1. Load from bytes
      2. Convert to grayscale
      3. Extract ROI (centre-crop)
      4. Resize to 256×256
      5. Enhance contrast
      6. Normalise & reshape to (1, 256, 256, 1)

    Args:
        image_bytes: Raw image file bytes (PNG, JPEG, DICOM-exported, etc.)

    Returns:
        np.ndarray of shape (1, 256, 256, 1) with float32 values in [0, 1].
    """
    img = load_image_from_bytes(image_bytes)
    img = convert_to_grayscale(img)
    img = extract_roi(img)
    img = resize_image(img)
    img = apply_clahe_enhancement(img)
    return image_to_array(img)


def get_processed_image_bytes(image_bytes: bytes) -> bytes:
    """
    Run the preprocessing pipeline and return the processed image as PNG bytes.
    Useful for uploading the processed version to S3 for audit / review.
    """
    img = load_image_from_bytes(image_bytes)
    img = convert_to_grayscale(img)
    img = extract_roi(img)
    img = resize_image(img)
    img = apply_clahe_enhancement(img)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
