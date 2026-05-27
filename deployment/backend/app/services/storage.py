from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings


ALLOWED_EXTENSIONS = {"pdf", "csv", "xlsx", "json", "xml"}
REJECTED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
MIME_BY_EXTENSION = {
    "pdf": "application/pdf",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
    "xml": "application/xml",
}


@dataclass
class StoredFile:
    file_bytes: bytes
    checksum_sha256: str
    size_bytes: int
    extension: str
    stored_filename: str
    storage_path: str


def ensure_storage_directories() -> None:
    settings = get_settings()
    for directory in [
        settings.app_documents_dir,
        settings.app_artifacts_dir,
        settings.app_temp_dir,
    ]:
        Path(directory).mkdir(parents=True, exist_ok=True)


def extension_from_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix


def validate_upload_type(filename: str) -> str:
    extension = extension_from_filename(filename)
    if extension in REJECTED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Standalone image uploads such as JPG, JPEG, and PNG are not supported.",
        )
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Supported types are PDF, CSV, XLSX, JSON, and XML.",
        )
    return extension


async def read_and_store_upload(
    file: UploadFile,
    filing_id: str,
    document_id: str,
    version_number: int,
) -> StoredFile:
    settings = get_settings()
    extension = validate_upload_type(file.filename or "")
    file_bytes = await file.read()
    checksum = sha256(file_bytes).hexdigest()
    stored_filename = f"{uuid4().hex}.{extension}"
    target_dir = Path(settings.app_documents_dir) / filing_id / document_id / f"v{version_number}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / stored_filename
    target_path.write_bytes(file_bytes)

    return StoredFile(
        file_bytes=file_bytes,
        checksum_sha256=checksum,
        size_bytes=len(file_bytes),
        extension=extension,
        stored_filename=stored_filename,
        storage_path=str(target_path),
    )

