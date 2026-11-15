"""MinIO (S3-compatible) client for document blob storage."""

from __future__ import annotations

from minio import Minio

from app.config import get_settings

_minio: Minio | None = None


def get_minio_client() -> Minio:
    """Return a shared MinIO client."""
    global _minio
    if _minio is None:
        settings = get_settings()
        _minio = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
    return _minio


def ensure_bucket_exists() -> None:
    """Create bucket if missing (call at startup)."""
    client = get_minio_client()
    settings = get_settings()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
