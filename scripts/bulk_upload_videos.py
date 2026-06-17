import os
import re
import json
import asyncio
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.library import ExerciseVideo
from app.services.s3_service import upload_bytes_to_s3

# ── Configuration (use environment variables or defaults) ──────────────────────
VIDEO_DIR = os.getenv("VIDEO_UPLOAD_DIR", "./local_videos")
METADATA_FILE = os.path.join(VIDEO_DIR, "video_metadata.json")

# ── Constants (match app/api/v1/video.py conventions) ──────────────────────────
VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
    "application/octet-stream",
}


def category_to_folder(category: str) -> str:
    """Convert category to S3 folder name (matches API convention)."""
    folder = re.sub(r"[^a-z0-9]+", "-", category.strip().lower()).strip("-")
    return folder or "uncategorized"


def blank_to_none(value: str | None) -> str | None:
    """Convert blank strings to None (matches API convention)."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


async def bulk_upload() -> dict:
    """
    Bulk upload exercise videos to S3 and database.
    
    Returns:
        dict: Statistics about the upload process
    """
    if not os.path.exists(METADATA_FILE):
        print(f"Error: {METADATA_FILE} not found.")
        return {"success": 0, "failed": 0, "skipped": 0}

    with open(METADATA_FILE, "r") as f:
        metadata_list = json.load(f)

    db: Session = SessionLocal()
    stats = {"success": 0, "failed": 0, "skipped": 0}

    try:
        for index, meta in enumerate(metadata_list, start=1):
            filepath = os.path.join(VIDEO_DIR, meta["filename"])
            
            # Validate file exists
            if not os.path.exists(filepath):
                print(f"[{index}/{len(metadata_list)}] ⚠️  Skipped: {meta['filename']} (File not found)")
                stats["skipped"] += 1
                continue
            
            print(f"[{index}/{len(metadata_list)}] Processing {meta['filename']}...")

            # Validate file type
            file_ext = Path(filepath).suffix.lower()
            valid_extensions = {".mp4", ".webm", ".mov", ".mkv"}
            if file_ext not in valid_extensions:
                print(f"  -> ❌ Invalid file type '{file_ext}'. Expected: {valid_extensions}")
                stats["failed"] += 1
                continue

            # 1. Upload to S3 (category-based folder, matching API convention)
            category = meta.get("category", "uncategorized").strip()
            folder = category_to_folder(category)
            s3_key = f"{folder}/{meta['filename']}"
            
            with open(filepath, "rb") as video_file:
                file_bytes = video_file.read()
                
            try:
                saved_key = await upload_bytes_to_s3(
                    data=file_bytes, 
                    key=s3_key, 
                    content_type="video/mp4"  # Default to mp4, can be enhanced with mime-type detection
                )
            except Exception as e:
                print(f"  -> ❌ S3 Upload failed for {meta['filename']}: {e}")
                stats["failed"] += 1
                continue

            # 2. Insert into Database (with database refresh to get video_id)
            try:
                new_video = ExerciseVideo(
                    title=meta["title"].strip(),
                    description=blank_to_none(meta.get("description")),
                    s3_url=saved_key,
                    thumbnail_url=blank_to_none(meta.get("thumbnail_url")),
                    kl_grade_min=int(meta["kl_grade_min"]),
                    kl_grade_max=int(meta["kl_grade_max"]),
                    category=category,
                    difficulty=meta.get("difficulty", "beginner").strip() or "beginner",
                    duration_seconds=int(meta["duration_seconds"]) if meta.get("duration_seconds") else None
                )
                
                db.add(new_video)
                db.commit()
                db.refresh(new_video)  # Get auto-generated video_id
                
                print(f"  -> ✅ Successfully uploaded (video_id={new_video.video_id}, s3_key={saved_key})")
                stats["success"] += 1

            except Exception as e:
                print(f"  -> ❌ Database insert failed for {meta['filename']}: {e}")
                db.rollback()
                stats["failed"] += 1

    except Exception as e:
        print(f"\n❌ Script aborted due to error: {e}")
        db.rollback()
    finally:
        db.close()
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 Upload Summary:")
    print(f"   ✅ Success: {stats['success']}")
    print(f"   ❌ Failed: {stats['failed']}")
    print(f"   ⚠️  Skipped: {stats['skipped']}")
    print(f"{'='*60}")
    
    return stats

if __name__ == "__main__":
    # Use asyncio.run to execute the async main function
    asyncio.run(bulk_upload())