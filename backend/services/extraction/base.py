from __future__ import annotations

from abc import ABC, abstractmethod

from schemas.common import DocumentFormat, ExtractedDocument


class BaseExtractor(ABC):
    """Port for pulling normalized text + a position map out of a source file.
    The redactor for the same format re-derives an identical block list from
    the same file, so offsets always line up between detection and replacement."""

    @property
    @abstractmethod
    def format(self) -> DocumentFormat: ...

    @abstractmethod
    def extract(self, file_path: str, document_id: str) -> ExtractedDocument: ...
