"""
Diagnostic Router
-----------------
Orchestrates the full diagnostic pipeline:
  1. Validate image ownership and existing reports
  2. Download image bytes from S3
  3. Validate image is a valid knee X-ray (Gatekeeper/ValidationAgent)
  4. Run the Diagnostic Agent (CNN) to predict KL grade
  5. Run the Recommendation Agent (RAG) for lifestyle advice
  6. Save the complete report to Neon DB
  7. Return the report to the client
"""

import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_db, RoleChecker
from app.schemas.report_schema import DiagnosticRequest, ReportOut
from app.models.image import Image
from app.models.report import Report
from app.models.user import User
from app.agents.diagnostic_agent import predict_kl_grade
from app.agents.recommendation_agent import generate_recommendation
from app.agents.validation_agent import validate_image
from app.services.image_processor import get_processed_image_bytes
from app.services.s3_service import upload_bytes_to_s3, generate_presigned_url

router = APIRouter()

# Patients and GPs can request diagnostics
allow_diagnose = RoleChecker(allowed_roles=["patient", "gp"])


@router.post("/analyze", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def analyze_xray(
    request: DiagnosticRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_diagnose),
):
    """
    Run the full diagnostic + recommendation pipeline on an uploaded X-ray.

    Flow:
      1. Validate the image belongs to the current user (or user is GP)
      2. Download the image bytes from S3
      3. Gatekeeper Validation → reject OOD/invalid images
      4. Diagnostic Agent → KL grade + confidence
      5. Upload processed image to S3 for audit trail
      6. Recommendation Agent → lifestyle advice + exercise videos
      7. Persist the Report in Neon DB
      8. Return the complete report
    """
    # ── 1. Validate image ownership ──────────────────────────────────────
    image = db.query(Image).filter(Image.image_id == request.image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    user = db.query(User).filter(User.email == current_user["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Patients can only analyze their own images; GPs can analyze any
    if current_user["role"] == "patient" and image.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="You can only analyze your own images")

    # Check if a report already exists for this image
    existing_report = db.query(Report).filter(Report.image_id == image.image_id).first()
    if existing_report:
        raise HTTPException(
            status_code=400,
            detail="A report already exists for this image. Use GET /reports/{report_id} to view it.",
        )

    # ── 2. Download image bytes from S3 ──────────────────────────────────
    try:
        presigned = generate_presigned_url(image.s3_url)
        async with httpx.AsyncClient() as client:
            response = await client.get(presigned, timeout=30.0)
        response.raise_for_status()
        image_bytes = response.content
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download image from S3: {e}",
        )

    # ── 3. Validate image is a valid knee X-ray (Gatekeeper) ────────────
    # This prevents OOD images from reaching the diagnostic CNN
    # Run in threadpool to prevent event loop blocking (CLIP inference is CPU-intensive)
    try:
        is_valid = await run_in_threadpool(validate_image, image_bytes)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="Image validation failed. Please upload a clear, weight-bearing knee X-ray.",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image validation failed: {e}",
        )

    # ── 4. Diagnostic Agent — CNN Inference ──────────────────────────────
    # Run in threadpool to prevent event loop blocking (TensorFlow inference is CPU-intensive)
    try:
        kl_grade, confidence, diagnosis_summary = await run_in_threadpool(
            predict_kl_grade, image_bytes
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Diagnostic Agent failed: {e}",
        )

    # ── 5. Upload processed image to S3 ──────────────────────────────────
    try:
        processed_bytes = get_processed_image_bytes(image_bytes)
        processed_key = f"processed/{image.image_id}_processed.png"
        processed_key_returned = await upload_bytes_to_s3(processed_bytes, processed_key)
        image.processed_s3_url = processed_key_returned
        db.commit()
    except Exception:
        pass  # Non-critical — don't fail the pipeline if processed upload fails

    # ── 6. Recommendation Agent — RAG ────────────────────────────────────
    # Run in threadpool to prevent event loop blocking (semantic search is CPU-intensive)
    try:
        rec_result = await run_in_threadpool(
            generate_recommendation,
            kl_grade=kl_grade,
            db=db,
            pain_level=request.pain_level,
            mobility_level=request.mobility_level,
            # New profile fields (April 2026)
            kinesiophobia=user.kinesiophobia,
            occupation_type=user.occupation_type,
            has_stairs=user.has_stairs,
            current_meds=json.loads(user.current_meds) if user.current_meds else None,
            sleep_quality=user.sleep_quality,
        )
    except Exception as e:
        # Recommendation is non-critical; provide diagnosis even if RAG fails
        rec_result = {
            "recommendation": "Recommendation service temporarily unavailable.",
            "lifestyle_plan": [],
            "warnings": [],
            "exercise_video_urls": [],
        }

    # ── 7. Persist Report ────────────────────────────────────────────────
    new_report = Report(
        image_id=image.image_id,
        user_id=user.user_id,
        kl_grade=kl_grade,
        confidence=confidence,
        diagnosis_summary=diagnosis_summary,
        recommendation=rec_result["recommendation"],
        lifestyle_plan=json.dumps(rec_result.get("lifestyle_plan", [])),
        warnings=json.dumps(rec_result.get("warnings", [])),
        exercise_video_urls=json.dumps(rec_result["exercise_video_urls"]),
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    # ── 8. Return Report ─────────────────────────────────────────────────
    return ReportOut(
        report_id=new_report.report_id,
        image_id=new_report.image_id,
        user_id=new_report.user_id,
        kl_grade=new_report.kl_grade,
        confidence=new_report.confidence,
        diagnosis_summary=new_report.diagnosis_summary,
        recommendation=new_report.recommendation,
        lifestyle_plan=json.loads(new_report.lifestyle_plan) if new_report.lifestyle_plan else [],
        warnings=json.loads(new_report.warnings) if new_report.warnings else [],
        exercise_video_urls=json.loads(new_report.exercise_video_urls)
        if new_report.exercise_video_urls
        else [],
        created_at=new_report.created_at,
    )


@router.get("/reports", response_model=list[ReportOut])
def get_my_reports(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_diagnose),
):
    """Get all diagnostic reports for the current user."""
    # Use eager loading to reduce 2 queries to 1
    user = db.query(User).options(
        joinedload(User.reports)
    ).filter(User.email == current_user["email"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reports = user.reports

    return [
        ReportOut(
            report_id=r.report_id,
            image_id=r.image_id,
            user_id=r.user_id,
            kl_grade=r.kl_grade,
            confidence=r.confidence,
            diagnosis_summary=r.diagnosis_summary,
            recommendation=r.recommendation,
            lifestyle_plan=json.loads(r.lifestyle_plan) if r.lifestyle_plan else [],
            warnings=json.loads(r.warnings) if r.warnings else [],
            medications=json.loads(r.medications) if r.medications else [],
            exercise_video_urls=json.loads(r.exercise_video_urls)
            if r.exercise_video_urls
            else [],
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_diagnose),
):
    """Get a specific diagnostic report by ID."""
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    user = db.query(User).filter(User.email == current_user["email"]).first()

    # Patients can only view their own reports
    if current_user["role"] == "patient" and report.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return ReportOut(
        report_id=report.report_id,
        image_id=report.image_id,
        user_id=report.user_id,
        kl_grade=report.kl_grade,
        confidence=report.confidence,
        diagnosis_summary=report.diagnosis_summary,
        recommendation=report.recommendation,
        lifestyle_plan=json.loads(report.lifestyle_plan) if report.lifestyle_plan else [],
        warnings=json.loads(report.warnings) if report.warnings else [],
        medications=json.loads(report.medications) if report.medications else [],
        exercise_video_urls=json.loads(report.exercise_video_urls)
        if report.exercise_video_urls
        else [],
        created_at=report.created_at,
    )
