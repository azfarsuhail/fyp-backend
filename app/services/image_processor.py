"""
Image Processor Service
-----------------------
Handles image preprocessing for the two CNNs in the backend:
  - Gatekeeper: MobileNetV2, 256x256 RGB, MobileNet scaling
  - Diagnostic: DenseNet121, 224x224 RGB, DenseNet preprocessing
"""

import io

import numpy as np
import tensorflow as tf
from PIL import Image, ImageOps


def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    """Open raw bytes as a PIL Image in RGB mode."""
    image = Image.open(io.BytesIO(image_bytes))
    return ImageOps.exif_transpose(image).convert("RGB")


def center_crop_image(img: Image.Image) -> Image.Image:
    """Crop the image to a centered square region."""
    width, height = img.size
    crop_size = min(width, height)
    left = (width - crop_size) // 2
    top = (height - crop_size) // 2
    right = left + crop_size
    bottom = top + crop_size
    return img.crop((left, top, right, bottom))


def prepare_image(image_bytes: bytes) -> Image.Image:
    """Load image bytes, normalize orientation, convert to RGB, and center crop."""
    image = load_image_from_bytes(image_bytes)
    return center_crop_image(image)


def process_for_gatekeeper(image_bytes: bytes) -> np.ndarray:
    """Prepare an image for the gatekeeper MobileNetV2 model."""
    image = prepare_image(image_bytes).resize((256, 256), Image.Resampling.LANCZOS)
    array = np.asarray(image, dtype=np.float32)
    array = (array / 127.5) - 1.0
    return np.expand_dims(array, axis=0)


def process_for_diagnostic(image_bytes: bytes) -> np.ndarray:
    """Prepare an image for the diagnostic DenseNet121 model."""
    image = prepare_image(image_bytes).resize((224, 224), Image.Resampling.LANCZOS)
    array = np.asarray(image, dtype=np.float32)
    array = tf.keras.applications.densenet.preprocess_input(array)
    return np.expand_dims(array, axis=0)


def get_processed_image_bytes(image_bytes: bytes) -> bytes:
    """Return the centered RGB image as PNG bytes for audit / review."""
    image = prepare_image(image_bytes)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
