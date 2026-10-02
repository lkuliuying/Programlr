import io
import stat
import struct
import time
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from apps.projects.archive import inspect_archive, normalize_path, prepare_archive
from apps.projects.exceptions import ImportRejected
from apps.projects.types import ImportLimits, PreparedSnapshot


def zip_bytes(
    entries: dict[str, bytes], compression: int = zipfile.ZIP_DEFLATED
) -> bytes:
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", compression=compression) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return result.getvalue()


def prepare(
    tmp_path: Path, data: bytes, limits: ImportLimits = ImportLimits()
) -> PreparedSnapshot:
    archive = tmp_path / "input.zip"
    archive.write_bytes(data)
    target = tmp_path / "prepared"
    target.mkdir(exist_ok=True)

    def write(path: Path, content: bytes) -> None:
        path.write_bytes(content)

    return prepare_archive(
        archive,
        target,
        limits,
        write,
        deadline=time.monotonic() + 10,
    )


@pytest.mark.parametrize(
    "name",
    [
        "../a.py",
        "/a.py",
        "C:/a.py",
        "\\\\server\\a.py",
        "a/../b.py",
        "a//b.py",
        "a/./b.py",
        "a\x00.py",
        "a:stream.py",
        "CON.py",
        "a./b.py",
        "a /b.py",
        "a\n.py",
        "a|b.py",
        "a//",
        "COM¹.py",
        "a/" * 34 + "b.py",
    ],
)
def test_rejects_ambiguous_paths(name: str) -> None:
    with pytest.raises(ImportRejected, match="INVALID_ARCHIVE"):
        normalize_path(name)


@pytest.mark.parametrize(
    "entries",
    [
        {"A.py": b"a", "a.py": b"b"},
        {"src/A.py": b"a", "SRC/b.py": b"b"},
        {"a": b"a", "a/b.py": b"b"},
        {"e\u0301.py": b"a", "é.py": b"b"},
        {"src\\a.py": b"a", "src/a.py": b"b"},
        {".git/../a.py": b"ignored"},
    ],
)
def test_all_entries_checked_before_filtering(
    tmp_path: Path, entries: dict[str, bytes]
) -> None:
    with pytest.raises(ImportRejected):
        prepare(tmp_path, zip_bytes(entries))


@pytest.mark.parametrize(
    "mode", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR]
)
def test_rejects_links_and_special_entries(tmp_path: Path, mode: int) -> None:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        info = zipfile.ZipInfo(".git/ignored")
        info.create_system = 3
        info.external_attr = (mode | 0o777) << 16
        archive.writestr(info, b"target")
    with pytest.raises(ImportRejected):
        prepare(tmp_path, data.getvalue())


@pytest.mark.parametrize(
    "data", [b"not a zip", b"", zip_bytes({}), zip_bytes({"README.md": b"no source"})]
)
def test_empty_corrupt_or_no_source_rejected(tmp_path: Path, data: bytes) -> None:
    with pytest.raises(ImportRejected):
        prepare(tmp_path, data)


def test_filtering_and_normalization(tmp_path: Path) -> None:
    entries = {
        "backend\\a.py": b"\xef\xbb\xbfa\r\nb\rc\n",
        "frontend/a.tsx": b"",
        ".env": b"synthetic-excluded",
        ".env.example": b"synthetic-excluded",
        "keys/private.pem": b"synthetic-excluded",
        "node_modules/a.js": b"synthetic-excluded",
        "dist/a.ts": b"synthetic-excluded",
        ".git/config": b"synthetic-excluded",
        "credentials.json": b"synthetic-excluded",
        "image.py": b"\x00binary",
        "legacy.py": b"\xff",
        "README.md": b"unsupported",
    }
    result = prepare(tmp_path, zip_bytes(entries))
    assert result["summary"]["accepted"] == 2
    assert result["summary"]["excluded"] == 7
    assert result["summary"]["skipped"] == 3
    assert result["summary"]["extracted_bytes"] == sum(map(len, entries.values()))
    assert "synthetic-excluded" not in str(result)
    first, empty = result["files"]
    assert first["file_path"] == "backend/a.py" and first["line_count"] == 3
    assert empty["line_count"] == 1
    assert (tmp_path / "prepared" / first["id"]).read_bytes() == b"a\nb\nc\n"


@pytest.mark.parametrize(
    "change",
    [
        {"archive_bytes": 10},
        {"declared_bytes": 9},
        {"extracted_bytes": 9},
        {"entries": 1},
        {"source_files": 1},
        {"source_bytes": 4},
    ],
)
def test_every_resource_budget(tmp_path: Path, change: dict[str, Any]) -> None:
    with pytest.raises(ImportRejected, match="ARCHIVE_LIMIT_EXCEEDED"):
        prepare(
            tmp_path,
            zip_bytes({"a.py": b"12345", "b.py": b"12345"}),
            replace(ImportLimits(), **change),
        )


def test_ignored_bomb_counts_actual_expansion(tmp_path: Path) -> None:
    with pytest.raises(ImportRejected) as error:
        prepare(
            tmp_path,
            zip_bytes({"node_modules/a": b"a" * 200000, "ok.py": b"ok"}),
            replace(ImportLimits(), extracted_bytes=1000),
        )
    assert error.value.reason == "extracted_bytes"


def test_understated_size_cannot_hide_actual_expansion(tmp_path: Path) -> None:
    data = bytearray(zip_bytes({"ignored.bin": b"a" * 200000, "ok.py": b"ok"}))
    central = data.index(b"PK\x01\x02")
    struct.pack_into("<I", data, central + 24, 1)
    with pytest.raises(ImportRejected) as error:
        prepare(tmp_path, bytes(data), replace(ImportLimits(), extracted_bytes=1000))
    assert error.value.reason == "extracted_bytes"


def test_crc_and_encryption_and_nul_rejected(tmp_path: Path) -> None:
    original = zip_bytes({"a.py": b"value = 1"}, zipfile.ZIP_STORED)
    bad_crc = bytearray(original)
    bad_crc[bad_crc.index(b"value")] ^= 1
    encrypted = bytearray(original)
    struct.pack_into("<H", encrypted, encrypted.index(b"PK\x01\x02") + 8, 1)
    nul_name = original.replace(b"a.py", b"a\x00py")
    for data in (bad_crc, encrypted, nul_name):
        with pytest.raises(ImportRejected):
            prepare(tmp_path, bytes(data))


def test_header_disagreement_and_truncation(tmp_path: Path) -> None:
    data = zip_bytes({"a.py": b"value = 1"})
    for broken in (data[:-30], data.replace(b"a.py", b"b.py", 1)):
        with pytest.raises(ImportRejected):
            prepare(tmp_path, broken)


def test_fake_directory_count_and_duplicate_entries(tmp_path: Path) -> None:
    data = bytearray(zip_bytes({"a.py": b"a", "b.py": b"b"}))
    end = data.index(b"PK\x05\x06")
    struct.pack_into("<HH", data, end + 8, 1, 1)
    with pytest.raises(ImportRejected):
        prepare(tmp_path, bytes(data), replace(ImportLimits(), entries=1))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("a.py", b"first")
        with pytest.warns(UserWarning):
            archive.writestr("a.py", b"second")
    with pytest.raises(ImportRejected):
        prepare(tmp_path, buffer.getvalue())


def test_exact_limits_and_sparse_index(tmp_path: Path) -> None:
    data = b"x\n" * 1000
    result = prepare(
        tmp_path,
        zip_bytes({"a.py": data}),
        replace(
            ImportLimits(),
            source_bytes=len(data),
            declared_bytes=len(data),
            extracted_bytes=len(data),
            entries=1,
            source_files=1,
        ),
    )
    source = result["files"][0]
    assert source["line_count"] == 1000
    assert source["line_offsets"] == list(range(0, 2000, 256))


def test_inspection_does_not_execute_source(tmp_path: Path) -> None:
    archive = tmp_path / "input.zip"
    archive.write_bytes(zip_bytes({"setup.py": b"raise RuntimeError('must not run')"}))
    assert len(inspect_archive(archive, ImportLimits())) == 1


def test_zip64_and_executable_prefix_are_outside_supported_profile(
    tmp_path: Path,
) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        with archive.open("a.py", "w", force_zip64=True) as source:
            source.write(b"value = 1")
    for data in (buffer.getvalue(), b"executable" + zip_bytes({"a.py": b"a"})):
        with pytest.raises(ImportRejected):
            prepare(tmp_path, data)
