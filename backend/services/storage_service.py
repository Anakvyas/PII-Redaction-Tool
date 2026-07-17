"""File storage port + two adapters. LocalFileStorage is the zero-config
default (a directory on disk); S3FileStorage is the production adapter for
Railway/S3-compatible buckets. Both satisfy the same interface, so swapping
STORAGE_BACKEND in settings is the only change needed to go from one to the
other — nothing upstream (extractors, redactors, services) knows which is active.
"""
from __future__ import annotations

import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from config.settings import Settings
from core.exceptions import StorageError
from utils.signing import issue_token, verify_token


class FileStorage(ABC):
    @abstractmethod
    def save(self, key: str, data: BinaryIO) -> str:
        """Persist bytes under `key`; returns the storage_uri."""

    @abstractmethod
    def save_path(self, key: str, local_path: str) -> str:
        """Upload a file already on local disk (e.g. a redaction pipeline's output)."""

    @abstractmethod
    def path_for(self, storage_uri: str) -> str:
        """Return a local filesystem path usable by extractors/redactors."""

    @abstractmethod
    def signed_url(self, storage_uri: str, expires_in: int = 900) -> str: ...

    @abstractmethod
    def resolve_download(self, token_or_uri: str) -> str:
        """Given whatever `signed_url` produced, return a local path to stream."""


class LocalFileStorage(FileStorage):
    def __init__(self, settings: Settings) -> None:
        self._root = Path(settings.LOCAL_STORAGE_DIR)
        self._root.mkdir(parents=True, exist_ok=True)
        self._secret = settings.SECRET_KEY
        self._api_prefix = settings.API_PREFIX

    def _abs_path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if self._root.resolve() not in path.parents and path != self._root.resolve():
            raise StorageError("Refusing to write outside the storage root.")
        return path

    def save(self, key: str, data: BinaryIO) -> str:
        path = self._abs_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            shutil.copyfileobj(data, fh)
        return f"local://{key}"

    def save_path(self, key: str, local_path: str) -> str:
        path = self._abs_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, path)
        return f"local://{key}"

    def path_for(self, storage_uri: str) -> str:
        key = storage_uri.removeprefix("local://")
        path = self._abs_path(key)
        if not path.exists():
            raise StorageError(f"File not found for storage_uri '{storage_uri}'.")
        return str(path)

    def signed_url(self, storage_uri: str, expires_in: int = 900) -> str:
        token = issue_token(storage_uri, self._secret, expires_in)
        return f"{self._api_prefix}/files/download?token={token}"

    def resolve_download(self, token_or_uri: str) -> str:
        storage_uri = verify_token(token_or_uri, self._secret)
        return self.path_for(storage_uri)


class S3FileStorage(FileStorage):
    """S3-compatible adapter (AWS S3, Cloudflare R2, MinIO, ...) via boto3."""

    def __init__(self, settings: Settings) -> None:
        import boto3

        self._bucket = settings.S3_BUCKET
        if not self._bucket:
            raise StorageError("S3_BUCKET must be set when STORAGE_BACKEND=s3.")
        self._client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )

    def save(self, key: str, data: BinaryIO) -> str:
        self._client.upload_fileobj(data, self._bucket, key)
        return f"s3://{self._bucket}/{key}"

    def save_path(self, key: str, local_path: str) -> str:
        self._client.upload_file(local_path, self._bucket, key)
        return f"s3://{self._bucket}/{key}"

    def _split(self, storage_uri: str) -> tuple[str, str]:
        without_scheme = storage_uri.removeprefix("s3://")
        bucket, _, key = without_scheme.partition("/")
        return bucket, key

    def path_for(self, storage_uri: str) -> str:
        bucket, key = self._split(storage_uri)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(key).suffix)
        self._client.download_fileobj(bucket, key, tmp)
        tmp.close()
        return tmp.name

    def signed_url(self, storage_uri: str, expires_in: int = 900) -> str:
        bucket, key = self._split(storage_uri)
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_in
        )

    def resolve_download(self, token_or_uri: str) -> str:
        # S3 downloads happen via the presigned URL directly, browser -> S3.
        raise StorageError("Direct download resolution is not used for the S3 backend.")


def build_storage(settings: Settings) -> FileStorage:
    if settings.STORAGE_BACKEND == "s3":
        return S3FileStorage(settings)
    return LocalFileStorage(settings)
