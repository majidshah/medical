"""File storage abstraction.

MVP: local filesystem. The interface (save/load/delete) is designed so swapping
to S3/GCS/R2 later requires only a new implementation class and a config change,
with no call-site modifications.
"""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "application/pdf"}


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, content_type: str) -> str: ...

    @abstractmethod
    async def load(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str | None = None):
        self._base = Path(base_dir or settings.upload_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, content_type: str) -> str:
        ext = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "application/pdf": ".pdf",
        }.get(content_type, "")
        key = f"{uuid.uuid4()}{ext}"
        (self._base / key).write_bytes(data)
        return key

    async def load(self, key: str) -> bytes:
        path = self._base / key
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self._base / key
        if path.exists():
            path.unlink()


_backend: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    global _backend
    if _backend is None:
        _backend = LocalStorageBackend()
    return _backend


def set_storage_backend(backend: StorageBackend) -> None:
    global _backend
    _backend = backend
