"""
Validation Agent — Gatekeeper Model
------------------------------------
A binary classification agent that validates whether an uploaded image is a 
valid Knee X-ray or an Out-of-Distribution (OOD) image.

Purpose:
  Before running the main diagnostic CNN (which expects valid knee X-rays),
  we first validate the image to prevent:
  - Garbage uploads (random photos, documents, etc.)
  - Wrong body part images (hands, feet, hips, etc.)
  - Corrupt or malformed files
  - Non-medical images

Architecture:
  - Model: MobileNetV2 (pretrained, fine-tuned for binary classification)
  - Input: Raw image bytes (any format)
  - Output: Boolean (True = valid knee X-ray, False = OOD/invalid)
  - Threshold: 0.5 (sigmoid probability)

Singleton Pattern:
  - Model loaded once at module initialization
  - Reused across all requests for efficiency
"""

import io
import numpy as np
import tensorflow as tf
from PIL import Image
from typing import Optional


class ValidationAgent:
    """
    Gatekeeper validation agent using MobileNetV2.
    
    Loads the gatekeeper.keras model once and validates images
    before they reach the main diagnostic pipeline.
    """
    
    _instance: Optional["ValidationAgent"] = None
    _model: Optional[tf.keras.Model] = None
    
    def __new__(cls):
        """Singleton pattern - ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(ValidationAgent, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize or reuse the loaded model."""
        if ValidationAgent._model is None:
            self._load_model()
    
    def _load_model(self):
        """
        Load the Gatekeeper model from disk.
        
        This is called only once on first initialization.
        """
        model_path = "app/ml_assets/cnn_weights/gatekeeper.keras"
        
        try:
            ValidationAgent._model = tf.keras.models.load_model(model_path)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Gatekeeper model from {model_path}: {e}"
            )
    
    def validate_image(self, image_bytes: bytes) -> bool:
        """
        Validate whether an image is a valid knee X-ray.
        
        Args:
            image_bytes: Raw image bytes (any format: JPEG, PNG, etc.)
        
        Returns:
            True if valid knee X-ray, False if OOD/invalid/corrupt
        """
        try:
            # Step 1: Load image from bytes using PIL
            image = Image.open(io.BytesIO(image_bytes))
            
            # Step 2: Convert to RGB (MobileNetV2 requires 3 channels)
            # This handles grayscale, RGBA, P mode, etc.
            image = image.convert("RGB")
            
            # Step 3: Resize to model input size (256, 256)
            image = image.resize((256, 256), Image.Resampling.LANCZOS)
            
            # Step 4: Convert to numpy array
            image_array = np.array(image, dtype=np.float32)
            
            # Step 5: Add batch dimension → (1, 256, 256, 3)
            image_array = np.expand_dims(image_array, axis=0)
            
            # Step 6: Apply MobileNetV2 preprocessing (scale to [-1, 1])
            image_array = tf.keras.applications.mobilenet_v2.preprocess_input(image_array)
            
            # Step 7: Run inference
            prediction = ValidationAgent._model.predict(image_array, verbose=0)[0][0]
            
            # Step 8: Apply threshold
            # Sigmoid output: < 0.5 = valid, >= 0.5 = OOD
            return prediction < 0.5
            
        except Exception as e:
            # Any error (corrupt file, invalid format, etc.) → reject
            return False


# Global singleton instance
_gatekeeper: Optional[ValidationAgent] = None


def get_validation_agent() -> ValidationAgent:
    """
    Get the global ValidationAgent singleton instance.
    
    Returns:
        ValidationAgent: The gatekeeper instance
    """
    global _gatekeeper
    if _gatekeeper is None:
        _gatekeeper = ValidationAgent()
    return _gatekeeper


def validate_image(image_bytes: bytes) -> bool:
    """
    Convenience function to validate an image.
    
    Args:
        image_bytes: Raw image bytes
    
    Returns:
        True if valid knee X-ray, False otherwise
    """
    agent = get_validation_agent()
    return agent.validate_image(image_bytes)
