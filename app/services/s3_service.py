import os
import uuid
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

# ── S3 Configuration (loaded from .env) ──────────────────────────────────────
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "knee-oa-uploads")

# ── S3-compatible endpoints (MinIO / offline setup) ──────────────────────────
# Unset → AWS S3. S3_ENDPOINT_URL is what the API uses (e.g. http://minio:9000);
# S3_PUBLIC_ENDPOINT_URL is the host clients use to open presigned URLs
# (e.g. http://localhost:9000). SigV4 signs the host, so they must differ.
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL") or None
S3_PUBLIC_ENDPOINT_URL = os.getenv("S3_PUBLIC_ENDPOINT_URL") or S3_ENDPOINT_URL


def get_s3_client(endpoint_url: str | None = S3_ENDPOINT_URL):
    """
    Create a thread-safe S3 client with proper configuration.

    Returns:
        boto3 S3 client with retry configuration
    """
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
        endpoint_url=endpoint_url,
        config=boto3.session.Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"} if endpoint_url else {},
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            }
        )
    )


async def upload_file_to_s3(file: UploadFile, folder: str = "xrays") -> str:
    """
    Upload a file to S3 and return the object key (not the public URL).

    Args:
        file: The FastAPI UploadFile object.
        folder: S3 key prefix / folder name.

    Returns:
        The S3 object key for the uploaded object (e.g. "xrays/abc123.png").
    """
    # Generate a unique filename to avoid collisions
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    unique_name = f"{folder}/{uuid.uuid4().hex}.{ext}"

    # Create thread-safe S3 client with proper cleanup
    s3_client = get_s3_client()
    try:
        contents = await file.read()
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=unique_name,
            Body=contents,
            ContentType=file.content_type or "image/png",
        )
        return unique_name
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}")
    finally:
        s3_client.close()  # Properly close S3 client
        await file.seek(0)  # Reset file pointer in case it's needed again


async def upload_bytes_to_s3(
    data: bytes, key: str, content_type: str = "image/png"
) -> str:
    """
    Upload raw bytes (e.g. a processed image) to S3 and return the object key.

    Args:
        data: Raw bytes to upload.
        key: The full S3 object key (e.g. "processed/abc123.png").
        content_type: MIME type.

    Returns:
        The S3 object key that was uploaded.
    """
    # Create thread-safe S3 client with proper cleanup
    s3_client = get_s3_client()
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}")
    finally:
        s3_client.close()  # Properly close S3 client


def download_bytes_from_s3(key: str) -> bytes:
    """
    Download an object's bytes directly via the internal endpoint.

    Args:
        key: The S3 object key.

    Returns:
        The object's raw bytes.
    """
    s3_client = get_s3_client()
    try:
        return s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)["Body"].read()
    except ClientError as e:
        raise RuntimeError(f"S3 download failed: {e}")
    finally:
        s3_client.close()


def generate_presigned_url(key: str, expiration: int = 3600) -> str:
    """
    Generate a pre-signed URL for private S3 objects (e.g. patient X-rays).

    Args:
        key: The S3 object key.
        expiration: URL validity in seconds (default 1 hour).

    Returns:
        A temporary pre-signed URL string.
    """
    # Presigning is local crypto (no network call), so the public host is safe here
    s3_client = get_s3_client(S3_PUBLIC_ENDPOINT_URL)
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": key},
            ExpiresIn=expiration,
        )
        return url
    except ClientError as e:
        raise RuntimeError(f"Failed to generate pre-signed URL: {e}")
    finally:
        s3_client.close()  # Properly close S3 client


def get_presigned_url(key: str, expiration: int = 3600) -> str:
    """Alias for generate_presigned_url for clearer callsites."""
    return generate_presigned_url(key, expiration=expiration)
