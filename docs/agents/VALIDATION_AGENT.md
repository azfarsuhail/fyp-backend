# Validation Agent (Gatekeeper) - Implementation Guide

**Date:** April 18, 2026  
**Status:** ✅ Complete  
**Model:** MobileNetV2 Binary Classifier  
**Purpose:** Reject Out-of-Distribution (OOD) images before diagnostic pipeline

---

## 📋 Overview

The **Validation Agent** (also called "Gatekeeper") is a binary classification model that validates whether an uploaded image is a valid knee X-ray before it reaches the main diagnostic CNN.

**Why it's needed:**
- Prevents garbage uploads (random photos, documents, etc.)
- Blocks wrong body part images (hands, feet, hips, etc.)
- Rejects corrupt or malformed files
- Protects the diagnostic CNN from OOD inputs that could cause false predictions

---

## 🏗️ Architecture

### File Location
`app/agents/validation_agent.py`

### Model Details
- **Architecture:** MobileNetV2 (pretrained, fine-tuned for binary classification)
- **Input:** Raw image bytes (any format: JPEG, PNG, etc.)
- **Output:** Single probability (sigmoid activation)
- **Threshold:** 0.5 (< 0.5 = valid, ≥ 0.5 = OOD)
- **Input Size:** 256×256×3 (RGB)

### Design Pattern: Singleton
- Model loaded **once** at module initialization
- Reused across all requests for efficiency
- No repeated disk I/O or model loading overhead

---

## 🔧 Implementation Details

### 1. Model Loading (Singleton)

```python
class ValidationAgent:
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
        """Load the Gatekeeper model from disk (called once)."""
        model_path = "app/ml_assets/cnn_weights/gatekeeper.keras"
        ValidationAgent._model = tf.keras.models.load_model(model_path)
```

**Key Points:**
- Model path: `app/ml_assets/cnn_weights/gatekeeper.keras`
- Loaded on first initialization
- Shared across all requests
- Raises `RuntimeError` if loading fails

---

### 2. Image Preprocessing (CRITICAL)

**IMPORTANT:** The Gatekeeper uses **MobileNetV2** which requires **3-channel RGB**, while the main Diagnostic CNN uses **1-channel Grayscale**.

```python
def validate_image(self, image_bytes: bytes) -> bool:
    """Validate whether an image is a valid knee X-ray."""
    try:
        # Step 1: Load image from bytes using PIL
        image = Image.open(io.BytesIO(image_bytes))
        
        # Step 2: Convert to RGB (MobileNetV2 requires 3 channels)
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
        return prediction < 0.5
        
    except Exception as e:
        # Any error (corrupt file, invalid format, etc.) → reject
        return False
```

**Preprocessing Steps Explained:**

| Step | Operation | Purpose |
|------|-----------|---------|
| 1 | `PIL.Image.open(io.BytesIO(image_bytes))` | Load image from raw bytes |
| 2 | `.convert("RGB")` | Convert to 3-channel RGB (critical!) |
| 3 | `.resize((256, 256), LANCZOS)` | Resize to model input size |
| 4 | `np.array(..., dtype=np.float32)` | Convert to numpy array |
| 5 | `np.expand_dims(..., axis=0)` | Add batch dimension |
| 6 | `mobilenet_v2.preprocess_input()` | Apply MobileNetV2-specific scaling |
| 7 | `model.predict()` | Run inference |
| 8 | `prediction < 0.5` | Apply threshold |

---

### 3. Inference & Return Logic

```python
# Sigmoid output: [0.0, 1.0]
if prediction < 0.5:
    return True  # Valid knee X-ray → proceed to diagnostic CNN
else:
    return False  # OOD/invalid → reject
```

**Error Handling:**
- Wrapped in `try/except` block
- Any exception (corrupt file, invalid format, parsing error) → returns `False`
- Gracefully rejects problematic images without crashing

---

## 🔗 Integration into Diagnostic Pipeline

### Updated Flow

```
┌─────────────────────────────────────────────────────────────┐
│  POST /api/v1/diagnostic/analyze                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Validate image ownership (user_id check)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Download image bytes from S3                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Gatekeeper Validation ⭐ NEW                            │
│     - validate_image(image_bytes)                           │
│     - If False → HTTP 400 error                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (only if True)
┌─────────────────────────────────────────────────────────────┐
│  4. Diagnostic Agent (CNN) → KL grade prediction            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Upload processed image to S3                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Recommendation Agent (RAG) → lifestyle advice           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Persist Report to Neon DB                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  8. Return Report to Client                                 │
└─────────────────────────────────────────────────────────────┘
```

### Code Integration

**Import:**
```python
from app.agents.validation_agent import validate_image
```

**Integration Point:**
```python
# ── 3. Download image bytes from S3 ──────────────────────────────────
try:
    response = requests.get(image.s3_url, timeout=30)
    response.raise_for_status()
    image_bytes = response.content
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Failed to download image from S3: {e}",
    )

# ── 4. Validate image is a valid knee X-ray (Gatekeeper) ────────────
# This prevents OOD images from reaching the diagnostic CNN
if not validate_image(image_bytes):
    raise HTTPException(
        status_code=400,
        detail="Image validation failed. Please upload a clear, weight-bearing knee X-ray.",
    )
```

**Error Response:**
```json
{
  "detail": "Image validation failed. Please upload a clear, weight-bearing knee X-ray."
}
```
HTTP Status: `400 Bad Request`

---

## 🧪 Testing Recommendations

### Unit Tests

1. **Valid Knee X-ray:**
   - Input: Known valid knee X-ray image
   - Expected: `True`

2. **OOD Image (wrong body part):**
   - Input: Hand X-ray, foot X-ray, hip X-ray
   - Expected: `False`

3. **Non-medical Image:**
   - Input: Photo of a cat, document, random photo
   - Expected: `False`

4. **Corrupt File:**
   - Input: Truncated/corrupted JPEG
   - Expected: `False` (exception caught)

5. **Invalid Format:**
   - Input: Text file, PDF, executable
   - Expected: `False` (exception caught)

6. **Threshold Edge Case:**
   - Input: Image with prediction ≈ 0.5
   - Expected: `False` (≥ 0.5 is OOD)

### Integration Tests

1. **Full Pipeline with Valid Image:**
   - Upload valid knee X-ray
   - Verify report generated successfully

2. **Full Pipeline with OOD Image:**
   - Upload hand X-ray
   - Verify HTTP 400 error returned
   - Verify no report created

3. **Full Pipeline with Corrupt File:**
   - Upload corrupted image
   - Verify HTTP 400 error returned

---

## 📊 Performance Considerations

### Model Loading
- **Cost:** ~50-100ms (first request only)
- **Strategy:** Singleton pattern avoids repeated loading

### Inference Time
- **Per Image:** ~10-30ms (on CPU)
- **Impact:** Minimal added latency to pipeline

### Memory Usage
- **Model Size:** ~15-20MB (MobileNetV2)
- **Strategy:** Shared across all requests

---

## 🔐 Error Handling

### Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| Model loading fails | Raises `RuntimeError` (startup failure) |
| Image parsing fails | Returns `False` (rejects image) |
| Inference fails | Returns `False` (rejects image) |
| Corrupt file | Returns `False` (exception caught) |

### User-Friendly Error Messages

```python
if not validate_image(image_bytes):
    raise HTTPException(
        status_code=400,
        detail="Image validation failed. Please upload a clear, weight-bearing knee X-ray.",
    )
```

**Why this message?**
- Clear and actionable
- Doesn't expose technical details
- Guides user to correct behavior

---

## 🚀 Deployment Checklist

- [ ] Gatekeeper model (`gatekeeper.keras`) exists in `app/ml_assets/cnn_weights/`
- [ ] Model was trained on knee X-rays (positive) and OOD images (negative)
- [ ] Model architecture matches MobileNetV2 input requirements (256×256×3)
- [ ] Model threshold validated on test set (aim for >95% accuracy on OOD detection)
- [ ] Singleton pattern tested (model loaded only once)
- [ ] Error handling tested (corrupt files, invalid formats)
- [ ] Integration tested with full diagnostic pipeline
- [ ] Performance tested (inference time <50ms per image)

---

## 📚 Related Documentation

- [Diagnostic Pipeline](../README.md)
- [Recommendation Agent](./RAG_AGENT_PROFILE_FILTERING.md)
- [Project Context](../../PROJECT_CONTEXT.md)

---

## 🔍 Troubleshooting

### Issue: Model loading fails at startup
**Solution:** Check that `gatekeeper.keras` exists in the correct path and is not corrupted.

### Issue: All images rejected (even valid ones)
**Solution:** Verify model threshold and check if model was trained correctly. May need to adjust threshold.

### Issue: OOD images not being rejected
**Solution:** Check model accuracy on validation set. May need retraining with more diverse OOD examples.

### Issue: Slow inference time
**Solution:** Consider using GPU acceleration or model quantization.

---

**Author:** AI Development Agent  
**Reviewed By:** Pending  
**Approved for Production:** Pending model validation
