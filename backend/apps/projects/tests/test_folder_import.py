import hashlib
import json
import time
import zipfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.projects.archive import inspect_archive, prepare_archive
from apps.projects.exceptions import ImportRejected
from apps.projects.folder import folder_limits, read_manifest, write_folder_archive


def manifest(paths: list[str]) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        "manifest.json",
        json.dumps(
            {
                "files": [
                    {"path": path, "index": index} for index, path in enumerate(paths)
                ]
            }
        ).encode(),
    )


def test_canonical_folder_archive_ignores_selection_order_and_metadata(
    tmp_path: Path,
) -> None:
    first = read_manifest(
        manifest(["b.py", "a.py"]),
        [SimpleUploadedFile("b.py", b"b=2\n"), SimpleUploadedFile("a.py", b"a=1\n")],
    )
    second = read_manifest(
        manifest(["a.py", "b.py"]),
        [
            SimpleUploadedFile("renamed.py", b"a=1\n"),
            SimpleUploadedFile("ignored.py", b"b=2\n"),
        ],
    )
    paths = [tmp_path / "a.zip", tmp_path / "b.zip"]
    for path, files in zip(paths, [first, second], strict=True):
        write_folder_archive(path, files, deadline=time.monotonic() + 10)
        inspect_archive(path, folder_limits())
    assert (
        hashlib.sha256(paths[0].read_bytes()).digest()
        == hashlib.sha256(paths[1].read_bytes()).digest()
    )
    assert folder_limits().archive_bytes > 100 * 1024 * 1024 + 4 * 1024 * 1024
    with zipfile.ZipFile(paths[0]) as archive:
        assert archive.namelist() == ["a.py", "b.py"]
        assert all(
            info.compress_type == zipfile.ZIP_STORED for info in archive.infolist()
        )


@pytest.mark.parametrize(
    "paths",
    [
        ["../a.py"],
        [".env/a.py"],
        ["node_modules/a.js"],
        ["private.key"],
        ["A.py", "a.py"],
        ["x.py", "x.py"],
    ],
)
def test_folder_rejects_unsafe_or_duplicate_paths(paths: list[str]) -> None:
    with pytest.raises(ImportRejected):
        read_manifest(
            manifest(paths), [SimpleUploadedFile("file", b"x") for _ in paths]
        )


def test_manifest_exact_file_mapping_and_limits() -> None:
    with pytest.raises(ImportRejected):
        read_manifest(manifest(["a.py"]), [])
    with pytest.raises(ImportRejected):
        read_manifest(
            manifest(["a.py"]), [SimpleUploadedFile("a.py", b"x" * (1024 * 1024 + 1))]
        )
    with pytest.raises(ImportRejected):
        read_manifest(
            SimpleUploadedFile("manifest", b'{"files":[{"path":"a.py","index":true}]}'),
            [SimpleUploadedFile("a.py", b"x")],
        )


def test_folder_uses_original_text_and_source_validation(tmp_path: Path) -> None:
    archive = tmp_path / "in.zip"
    write_folder_archive(
        archive,
        read_manifest(
            manifest(["requirements.txt", "a.py"]),
            [
                SimpleUploadedFile("r", b"django==5.2\n"),
                SimpleUploadedFile("a", b"x=1\r\n"),
            ],
        ),
        deadline=time.monotonic() + 10,
    )
    prepared = tmp_path / "prepared"
    prepared.mkdir()

    def write(path: Path, data: bytes) -> None:
        path.write_bytes(data)

    result = prepare_archive(
        archive,
        prepared,
        folder_limits(),
        write,
        deadline=time.monotonic() + 10,
    )
    assert result["summary"]["accepted"] == 2
    source = next(item for item in result["files"] if item["file_path"] == "a.py")
    assert (prepared / source["id"]).read_bytes() == b"x=1\n"


def test_folder_count_and_total_limits_include_manifest_sources() -> None:
    paths = [f"{index}.py" for index in range(2001)]
    with pytest.raises(ImportRejected):
        read_manifest(manifest(paths), [SimpleUploadedFile("file", b"") for _ in paths])
    paths = [f"{index}.py" for index in range(101)]
    files = [SimpleUploadedFile("file", b"") for _ in paths]
    for source in files:
        source.size = 1024 * 1024
    assert len(read_manifest(manifest(paths[:100]), files[:100])) == 100
    with pytest.raises(ImportRejected):
        read_manifest(manifest(paths), files)
