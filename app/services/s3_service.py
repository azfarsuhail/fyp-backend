import os
import uuid
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

# ── S3 Configuration (loaded from .env) ──────────────────────────────────────
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "knee-oa-uploads")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)


async def upload_file_to_s3(file: UploadFile, folder: str = "xrays") -> str:
    """
    Upload a file to S3 and return its public URL.

    Args:
        file: The FastAPI UploadFile object.
        folder: S3 key prefix / folder name.

    Returns:
        The full S3 URL of the uploaded object.
    """
    # Generate a unique filename to avoid collisions
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    unique_name = f"{folder}/{uuid.uuid4().hex}.{ext}"

    try:
        contents = await file.read()
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=unique_name,
            Body=contents,
            ContentType=file.content_type or "image/png",
        )
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_name}"
        return s3_url
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}")
    finally:
        await file.seek(0)  # Reset file pointer in case it's needed again


async def upload_bytes_to_s3(
    data: bytes, key: str, content_type: str = "image/png"
) -> str:
    """
    Upload raw bytes (e.g. a processed image) to S3.

    Args:
        data: Raw bytes to upload.
        key: The full S3 object key (e.g. "processed/abc123.png").
        content_type: MIME type.

    Returns:
        The full S3 URL.
    """
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}")


def generate_presigned_url(key: str, expiration: int = 3600) -> str:
    """
    Generate a pre-signed URL for private S3 objects (e.g. patient X-rays).

    Args:
        key: The S3 object key.
        expiration: URL validity in seconds (default 1 hour).

    Returns:
        A temporary pre-signed URL string.
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": key},
            ExpiresIn=expiration,
        )
        return url
    except ClientError as e:
        raise RuntimeError(f"Failed to generate pre-signed URL: {e}")
