import hashlib
import json
import os
import shutil
import stat
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from django.conf import settings

from apps.projects.exceptions import ImportRejected
from apps.projects.types import ImportLimits


def import_limits() -> ImportLimits:
    return ImportLimits(**settings.IMPORT_LIMITS)


def storage_root() -> Path:
    root = Path(settings.IMPORT_STORAGE_ROOT)
    if not root.is_absolute() or root.is_symlink() or root.resolve() != root:
        raise ImportRejected("unsafe_storage_root", storage=True)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in ("staging", "snapshots"):
        child = root / name
        child.mkdir(exist_ok=True, mode=0o700)
        if child.is_symlink() or not child.is_dir():
            raise ImportRejected("unsafe_storage_root", storage=True)
    return root


@contextmanager
def file_lock(path: Path, *, blocking: bool = True) -> Iterator[bool]:
    import fcntl

    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
        else:
            try:
                yield True
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


@contextmanager
def stage_lock(identifier: uuid.UUID, *, create: bool = False) -> Iterator[Path | None]:
    root = storage_root()
    stage = root / "staging" / str(identifier)
    # 建目录与取得锁必须同恢复扫描互斥，防止扫描器误删尚未建立数据库记录的上传。
    with file_lock(root / ".guard"):
        if create:
            stage.mkdir(mode=0o700)
            sync_directory(stage.parent)
        if not stage.is_dir() or stage.is_symlink():
            yield None
            return
        lock = file_lock(stage / ".lock", blocking=False)
        acquired = lock.__enter__()
    try:
        yield stage if acquired else None
    finally:
        lock.__exit__(None, None, None)


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_bytes(path: Path, content: bytes) -> None:
    with path.open("xb") as target:
        target.write(content)
        target.flush()
        os.fsync(target.fileno())


def read_bytes(path: Path, maximum: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ImportRejected("invalid_storage_entry", storage=True)
        data = source.read(maximum + 1)
        if len(data) > maximum:
            raise ImportRejected("invalid_storage_size", storage=True)
        return data


def write_manifest(directory: Path, manifest: dict[str, Any]) -> str:
    content = json.dumps(
        manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode()
    write_bytes(directory / ".complete.json", content)
    sync_directory(directory)
    return hashlib.sha256(content).hexdigest()


def publish_directory(prepared: Path, identifier: uuid.UUID) -> Path:
    destination = storage_root() / "snapshots" / str(identifier)
    if destination.exists():
        raise ImportRejected("snapshot_already_exists", storage=True)
    prepared.rename(destination)
    sync_directory(destination.parent)
    sync_directory(prepared.parent)
    return destination


def remove_owned_directory(path: Path, parent: Path) -> None:
    if (
        path.parent != parent
        or path.is_symlink()
        or path.resolve().parent != parent.resolve()
    ):
        raise ImportRejected("unsafe_cleanup_path", storage=True)
    uuid.UUID(path.name)
    if path.exists():
        shutil.rmtree(path)
        sync_directory(parent)
