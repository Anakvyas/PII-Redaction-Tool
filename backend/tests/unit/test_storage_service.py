"""Tests for LocalFileStorage — in particular the path-traversal guard in
_abs_path, which is the only thing standing between a crafted storage key
and reading/writing outside the storage root."""
import io

import pytest

from config.settings import Settings
from core.exceptions import StorageError
from services.storage_service import LocalFileStorage


def _storage(tmp_path) -> LocalFileStorage:
    settings = Settings(LOCAL_STORAGE_DIR=str(tmp_path / "storage"), SECRET_KEY="test-secret")
    return LocalFileStorage(settings)


class TestSaveAndPathFor:
    def test_round_trips_bytes_through_save_and_path_for(self, tmp_path):
        storage = _storage(tmp_path)
        uri = storage.save("originals/doc.txt", io.BytesIO(b"hello world"))
        assert uri == "local://originals/doc.txt"

        path = storage.path_for(uri)
        assert open(path, "rb").read() == b"hello world"

    def test_path_for_missing_file_raises(self, tmp_path):
        storage = _storage(tmp_path)
        with pytest.raises(StorageError):
            storage.path_for("local://originals/does-not-exist.txt")


class TestPathTraversalGuard:
    def test_rejects_parent_directory_traversal_on_save(self, tmp_path):
        storage = _storage(tmp_path)
        with pytest.raises(StorageError):
            storage.save("../../../../etc/passwd", io.BytesIO(b"pwned"))

    def test_rejects_parent_directory_traversal_on_path_for(self, tmp_path):
        storage = _storage(tmp_path)
        with pytest.raises(StorageError):
            storage.path_for("local://../../../../etc/passwd")

    def test_traversal_attempt_does_not_write_outside_root(self, tmp_path):
        storage = _storage(tmp_path)
        outside_target = tmp_path / "escaped.txt"
        try:
            storage.save("../escaped.txt", io.BytesIO(b"pwned"))
        except StorageError:
            pass
        assert not outside_target.exists()


class TestSignedUrlRoundTrip:
    def test_signed_url_resolves_back_to_the_same_local_path(self, tmp_path):
        storage = _storage(tmp_path)
        uri = storage.save("originals/doc.txt", io.BytesIO(b"secret contents"))
        signed = storage.signed_url(uri, expires_in=900)

        token = signed.split("token=", 1)[1]
        resolved_path = storage.resolve_download(token)
        assert open(resolved_path, "rb").read() == b"secret contents"

    def test_expired_signed_url_is_rejected(self, tmp_path):
        storage = _storage(tmp_path)
        uri = storage.save("originals/doc.txt", io.BytesIO(b"secret contents"))
        signed = storage.signed_url(uri, expires_in=-1)
        token = signed.split("token=", 1)[1]

        with pytest.raises(Exception):
            storage.resolve_download(token)
