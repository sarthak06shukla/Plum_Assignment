import hashlib
from pathlib import Path

from fastapi import UploadFile

from backend.app.core.config import get_settings


ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}


class UploadValidationError(ValueError):
    pass


class DocumentUploadService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def validate_and_store(self, file: UploadFile, claim_id: str, document_type: str) -> tuple[Path, int, str]:
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise UploadValidationError(f"Unsupported file type: {file.content_type}")

        content = await file.read()
        if not content:
            raise UploadValidationError("Upload is empty or corrupted")

        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise UploadValidationError(f"File exceeds {self.settings.max_upload_mb}MB limit")

        suffix = ALLOWED_MIME_TYPES[file.content_type]
        digest = hashlib.sha256(content).hexdigest()[:16]
        safe_name = f"{claim_id}_{document_type.lower()}_{digest}{suffix}"
        destination = self.settings.upload_dir / safe_name
        destination.write_bytes(content)

        return destination, len(content), file.content_type
