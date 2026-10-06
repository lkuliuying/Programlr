"""把已校验的目录文件转为确定性归档，复用快照归档安全边界。"""

from __future__ import annotations

import json
import time
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from django.core.files.uploadedfile import UploadedFile

from apps.projects.archive import disposition, normalize_path
from apps.projects.exceptions import ImportRejected
from apps.projects.types import ImportLimits

FOLDER_BYTES = 100 * 1024 * 1024
MANIFEST_BYTES = 4 * 1024 * 1024
FOLDER_FILES = 2000
FOLDER_HEADER_BYTES = FOLDER_FILES * (76 + 2 * 1024) + 22
FOLDER_BODY_BYTES = 110 * 1024 * 1024
CODEC_VERSION = "folder-zip-stored/1.0.0"


def folder_limits() -> ImportLimits:
    return ImportLimits(
        archive_bytes=FOLDER_BYTES + FOLDER_HEADER_BYTES,
        declared_bytes=FOLDER_BYTES,
        extracted_bytes=FOLDER_BYTES,
        entries=FOLDER_FILES,
        source_files=FOLDER_FILES,
    )


def read_manifest(
    upload: UploadedFile[Any], files: Sequence[UploadedFile[Any]]
) -> list[tuple[str, UploadedFile[Any]]]:
    if (
        not 1 <= len(files) <= FOLDER_FILES
        or upload.size is None
        or not 0 < upload.size <= MANIFEST_BYTES
    ):
        raise ImportRejected("folder_input_limit", limit=True)
    try:
        document = json.loads(upload.read(MANIFEST_BYTES + 1))
    except (UnicodeError, ValueError):
        raise ImportRejected("invalid_folder_manifest") from None
    if (
        not isinstance(document, dict)
        or set(document) != {"files"}
        or not isinstance(document["files"], list)
        or len(document["files"]) != len(files)
    ):
        raise ImportRejected("invalid_folder_manifest")
    output: list[tuple[str, UploadedFile[Any]]] = []
    seen: set[str] = set()
    total = 0
    for position, item in enumerate(document["files"]):
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "index"}
            or type(item["index"]) is not int
            or item["index"] != position
            or not isinstance(item["path"], str)
        ):
            raise ImportRejected("invalid_folder_manifest")
        path = normalize_path(item["path"])
        if (
            path != item["path"]
            or disposition(path) != "source"
            or path.casefold() in seen
        ):
            raise ImportRejected("unsafe_folder_source")
        seen.add(path.casefold())
        upload_file = files[position]
        if upload_file.size is None or not 0 <= upload_file.size <= 1024 * 1024:
            raise ImportRejected("source_limit", limit=True)
        total += upload_file.size
        if total > FOLDER_BYTES:
            raise ImportRejected("folder_bytes", limit=True)
        output.append((path, upload_file))
    return sorted(output, key=lambda value: value[0])


def write_folder_archive(
    path: Path, files: list[tuple[str, UploadedFile[Any]]], *, deadline: float
) -> None:
    with zipfile.ZipFile(
        path, "x", compression=zipfile.ZIP_STORED, allowZip64=False
    ) as archive:
        for name, source in files:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            info.compress_type = zipfile.ZIP_STORED
            with archive.open(info, "w") as target:
                actual = 0
                for chunk in source.chunks(64 * 1024):
                    actual += len(chunk)
                    if actual > 1024 * 1024 or time.monotonic() >= deadline:
                        raise ImportRejected("folder_receive_limit", limit=True)
                    target.write(chunk)
                if actual != source.size:
                    raise ImportRejected("folder_size_mismatch")
