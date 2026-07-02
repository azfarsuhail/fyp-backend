"""
Validation Agent — CLIP-based Gatekeeper
-----------------------------------------
A zero-shot classification agent that validates whether an uploaded image is a
valid Knee X-ray or an Out-of-Distribution (OOD) image.

Purpose:
    Before running the main diagnostic CNN (which expects valid knee X-rays),
    we first validate the image to prevent:
    - Garbage uploads (random photos, documents, etc.)
    - Wrong body part images (hands, feet, hips, etc.)
    - Corrupt or malformed files
    - Non-medical images

Architecture:
    - Model: CLIP (openai/clip-vit-base-patch32) via HuggingFace transformers
    - Method: Zero-shot image classification with natural language labels
    - Input: Raw image bytes (any format)
    - Output: Boolean (True = valid knee X-ray, False = OOD/invalid)
    - Threshold: 0.5 confidence for "a knee x-ray" label

Advantages over CNN:
    - No training data required
    - Better generalization to diverse OOD images
    - Understands semantic meaning of "knee x-ray"
    - More robust to edge cases

Singleton Pattern:
    - Pipeline loaded once at module initialization
    - Reused across all requests for efficiency
"""

import io
import sys
import traceback
from threading import Lock
from typing import Optional

import torch
from PIL import Image
from transformers import pipeline


class ValidationAgent:
    """
    Gatekeeper validation agent using CLIP zero-shot classification.
    
    Loads the CLIP pipeline once and validates images
    before they reach the main diagnostic pipeline.
    """
    
    _instance: Optional["ValidationAgent"] = None
    _pipeline: Optional[pipeline] = None
    _lock = Lock()
    
    # Candidate labels for zero-shot classification
    LABELS = [
        "a knee x-ray",
        "a black and white logo",
        "a regular photo of a person",
        "a scanned document",
        "a hand x-ray",
        "a chest x-ray",
    ]
    
    def __new__(cls):
        """Singleton pattern - ensure only one instance exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ValidationAgent, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize or reuse the loaded pipeline."""
        if ValidationAgent._pipeline is None:
            with ValidationAgent._lock:
                if ValidationAgent._pipeline is None:
                    self._load_model()
    
    def _load_model(self):
        """
        Load the CLIP zero-shot classification pipeline.
        
        This is called only once on first initialization.
        Uses GPU if available, otherwise falls back to CPU.
        """
        try:
            device = 0 if torch.cuda.is_available() else -1
            print(f"[INFO] Loading CLIP gatekeeper on device: {'GPU' if device == 0 else 'CPU'}", flush=True)
            
            ValidationAgent._pipeline = pipeline(
                "zero-shot-image-classification",
                model="openai/clip-vit-base-patch32",
                device=device
            )
            print("[INFO] CLIP gatekeeper loaded successfully", flush=True)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load CLIP Gatekeeper pipeline: {e}"
            )
    
    def validate_image(self, image_bytes: bytes) -> bool:
        """
        Validate whether an image is a valid knee X-ray using CLIP zero-shot classification.
        
        Args:
            image_bytes: Raw image bytes (any format: JPEG, PNG, etc.)
        
        Returns:
            True if valid knee X-ray, False if OOD/invalid/corrupt
        """
        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            print(f"[DEBUG] Loaded image size: {image.size}", flush=True)
            
            # Run zero-shot classification
            results = ValidationAgent._pipeline(image, candidate_labels=self.LABELS)
            
            # Get the top prediction
            best_guess = results[0]['label']
            confidence = results[0]['score']
            
            print(f"[DEBUG] CLIP Gatekeeper says: {best_guess} ({confidence:.4f})", flush=True)
            print(f"[DEBUG] Top 3 predictions:", flush=True)
            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result['label']}: {result['score']:.4f}", flush=True)
            
            # Check if it's a knee x-ray with sufficient confidence
            is_valid = best_guess == "a knee x-ray" and confidence > 0.5
            print(f"[DEBUG] Gatekeeper evaluation result: {is_valid}", flush=True)
            
            return is_valid

        except Exception as e:
            # Log full error details to stdout for debugging
            print(f"[ERROR] Validation error occurred: {str(e)}", flush=True)
            traceback.print_exc(file=sys.stdout)
            # Any error (corrupt file, invalid format, etc.) → reject
            return False


# Global singleton instance
_gatekeeper: Optional[ValidationAgent] = None
_gatekeeper_lock = Lock()


def get_validation_agent() -> ValidationAgent:
    """
    Get the global ValidationAgent singleton instance.
    
    Returns:
        ValidationAgent: The gatekeeper instance
    """
    global _gatekeeper
    if _gatekeeper is None:
        with _gatekeeper_lock:
            if _gatekeeper is None:
                _gatekeeper = ValidationAgent()
    return _gatekeeper


def validate_image(image_bytes: bytes) -> bool:
    """
    Validate whether an image is a valid knee X-ray using CLIP zero-shot classification.
    
    This is a module-level convenience function that uses the singleton ValidationAgent.
    """
    agent = get_validation_agent()
    try:
        # Load image from bytes
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        print(f"[DEBUG] Loaded image size: {image.size}", flush=True)
        
        # Run zero-shot classification
        results = ValidationAgent._pipeline(image, candidate_labels=ValidationAgent.LABELS)
        
        # Get the top prediction
        best_guess = results[0]['label']
        confidence = results[0]['score']
        
        print(f"[DEBUG] CLIP Gatekeeper says: {best_guess} ({confidence:.4f})", flush=True)
        print(f"[DEBUG] Top 3 predictions:", flush=True)
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result['label']}: {result['score']:.4f}", flush=True)
        
        # Check if it's a knee x-ray with sufficient confidence
        is_valid = best_guess == "a knee x-ray" and confidence > 0.5
        print(f"[DEBUG] Gatekeeper evaluation result: {is_valid}", flush=True)
        
        return is_valid

    except Exception as e:
        # CRITICAL: This exposes any underlying environment/library crash
        print(f"[ERROR] Gatekeeper pipeline crashed! Details: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return False