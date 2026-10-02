from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True)
class ImportLimits:
    archive_bytes: int = 20 * 1024 * 1024
    declared_bytes: int = 100 * 1024 * 1024
    extracted_bytes: int = 100 * 1024 * 1024
    entries: int = 5000
    source_files: int = 2000
    source_bytes: int = 1024 * 1024


class ImportSummary(TypedDict):
    entries: int
    accepted: int
    excluded: int
    skipped: int
    rejected: int
    declared_bytes: int
    extracted_bytes: int
    reasons: dict[str, int]


class PreparedFile(TypedDict):
    id: str
    file_path: str
    sha256: str
    size_bytes: int
    line_count: int
    line_offsets: list[int]
    encoding: str


class PreparedSnapshot(TypedDict):
    files: list[PreparedFile]
    summary: ImportSummary
