# Changelog — 2026-06-02

Summary
-------
- Switched S3 usage from storing and returning public object URLs to storing S3 object keys in the database and generating short-lived presigned URLs for client access.

Files changed
-------------
- `app/services/s3_service.py`: uploads now return S3 object keys; added `generate_presigned_url()` helper.
- `app/api/v1/upload.py`: store object key in DB; return presigned URL to client.
- `app/api/v1/diagnostic.py`: download original image using a presigned URL; store processed object key.
- `app/services/mobile_sync.py`: return presigned URLs to mobile clients.
- `app/agents/recommendation_agent.py`: return presigned URLs for exercise videos.
- Tests and fixtures updated to use object keys and to mock `generate_presigned_url` where needed.

Why this change
---------------
- Storing private objects and using presigned URLs improves security by keeping S3 objects private and only granting temporary access. This reduces accidental public exposure and centralises access control through IAM.

Deployment & Environment
------------------------
- Environment variables required (set in `.env` or use an instance profile):
  - `S3_BUCKET_NAME` — target bucket name
  - `AWS_REGION` — region (default `ap-south-1`)
  - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — or use an IAM role attached to the host/container
- IAM permissions recommended for the application role/user:
  - `s3:PutObject` on `arn:aws:s3:::<bucket>/*`
  - `s3:GetObject` on `arn:aws:s3:::<bucket>/*`
  - (Optional) `s3:ListBucket` on `arn:aws:s3:::<bucket>` if listing is required

Testing
-------
- All unit tests were updated and executed inside the project Docker container. Test run:

  - `docker compose exec api pytest -q` → `107 passed, 0 failed`

Migration notes
---------------
- Database: no schema change — `s3_url` column now stores the object key (string) instead of a public URL. Existing records with full URLs will continue to work for now, but consider a one-time migration to convert public URLs to object keys (or leave them — the presigning helper can accept a full URL in a migration script).
- Client compatibility: API responses now contain presigned URLs (same `s3_url` field in responses). Clients should treat `s3_url` as a temporary download link and not cache it long-term.

Security & Bucket Policy
------------------------
- Keep bucket objects private. Avoid public-read ACLs.
- Example minimal bucket policy allows only the application IAM role and no public access.

Contact
-------
If you want, I can add a small migration script to convert existing public S3 URLs to object keys in the DB, or a maintenance note for ops to rotate keys and validate bucket policy.
