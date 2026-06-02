"""
Upload Router
-------------
Handles knee X-ray image uploads to AWS S3 and records metadata in Neon DB.
Protected: Only authenticated patients and GPs can upload.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, RoleChecker
from app.schemas.image_schema import ImageUploadResponse
from app.models.image import Image
from app.services.s3_service import upload_file_to_s3, generate_presigned_url

router = APIRouter()

# Only patients and GPs can upload X-rays
allow_upload = RoleChecker(allowed_roles=["patient", "gp"])

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/dicom"}


@router.post("/", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_xray(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_upload),
):
    """
    Upload a knee X-ray image.

    - Validates file type
    - Uploads original image to S3
    - Creates an Image record in the database
    - Returns the image metadata
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: {ALLOWED_CONTENT_TYPES}",
        )

    # Upload to S3 (returns object key)
    try:
        s3_key = await upload_file_to_s3(file, folder="xrays")
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Get user_id from the database using the email in the JWT
    from app.models.user import User

    user = db.query(User).filter(User.email == current_user["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Save image record to Neon DB
    new_image = Image(
        user_id=user.user_id,
        s3_url=s3_key,
        file_name=file.filename,
        content_type=file.content_type,
    )
    db.add(new_image)
    db.commit()
    db.refresh(new_image)

    # Return a presigned URL to the client while keeping the object key in DB
    try:
        new_image.s3_url = generate_presigned_url(new_image.s3_url)
    except Exception:
        # Fallback: return the raw key if presigned URL generation fails
        new_image.s3_url = new_image.s3_url

    return new_image
