import hashlib
import re
import stat
import struct
import time
import unicodedata
import uuid
import zipfile
import zlib
from collections.abc import Callable, Iterator
from pathlib import Path

from apps.projects.exceptions import ImportRejected
from apps.projects.types import (
    ImportLimits,
    ImportSummary,
    PreparedFile,
    PreparedSnapshot,
)

SOURCE_EXTENSIONS = (".py", ".js", ".jsx", ".ts", ".tsx")
EXCLUDED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    ".idea",
    ".vscode",
    ".ssh",
}
EXCLUDED_SUFFIXES = {
    ".pem",
    ".key",
    ".crt",
    ".cer",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
}
EXCLUDED_NAMES = {
    "credentials",
    "credentials.json",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    ".netrc",
    ".npmrc",
    ".pypirc",
}
CHUNK_SIZE = 64 * 1024


def check_directory_budget(path: Path, limits: ImportLimits) -> None:
    # 在 ZipFile 创建条目对象前限制中央目录，避免伪造条目数导致无界元数据分配。
    size = path.stat().st_size
    with path.open("rb") as source:
        if source.read(4) not in (b"PK\x03\x04", b"PK\x05\x06"):
            raise ImportRejected("unsupported_prefix")
        source.seek(max(0, size - 65557))
        tail = source.read(65557)
        offset = tail.rfind(b"PK\x05\x06")
        if offset < 0 or len(tail) - offset < 22:
            raise ImportRejected("corrupt_directory")
        disk, central_disk, disk_count, count, central_size, central_offset, comment = (
            struct.unpack_from("<HHHHIIH", tail, offset + 4)
        )
        end_offset = size - len(tail) + offset
        if (
            disk
            or central_disk
            or disk_count != count
            or offset + 22 + comment != len(tail)
            or central_offset + central_size != end_offset
        ):
            raise ImportRejected("unsupported_directory")
        if count > limits.entries:
            raise ImportRejected("entries", limit=True)
        source.seek(central_offset)
        observed = 0
        while source.tell() < end_offset:
            header = source.read(46)
            if len(header) != 46 or header[:4] != b"PK\x01\x02":
                raise ImportRejected("corrupt_directory")
            observed += 1
            if observed > limits.entries:
                raise ImportRejected("entries", limit=True)
            lengths = struct.unpack_from("<HHH", header, 28)
            source.seek(sum(lengths), 1)
        if source.tell() != end_offset or observed != count:
            raise ImportRejected("directory_count_mismatch")


def normalize_path(raw: str) -> str:
    name = unicodedata.normalize("NFC", raw.replace("\\", "/"))
    parts = name.removesuffix("/").split("/")
    if (
        not name
        or name.startswith("/")
        or len(name.encode("utf-8")) > 1024
        or len(parts) > 32
        or any(
            part in ("", ".", "..")
            or part.endswith((" ", "."))
            or len(part.encode("utf-8")) > 255
            or any(
                ord(char) < 32 or ord(char) == 127 or char in ':<>"|?*' for char in part
            )
            or re.fullmatch(
                r"(?i)(con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?", part
            )
            for part in parts
        )
    ):
        raise ImportRejected("unsafe_path")
    return "/".join(parts)


def disposition(path: str) -> str:
    parts = path.casefold().split("/")
    name = parts[-1]
    if (
        any(
            part in EXCLUDED_DIRECTORIES or part == ".env" or part.startswith(".env.")
            for part in parts
        )
        or name in EXCLUDED_NAMES
        or Path(name).suffix in EXCLUDED_SUFFIXES
        or name.startswith(("credentials.", "secrets.", "id_rsa.", "id_ed25519."))
    ):
        return "excluded"
    return "source" if Path(name).suffix in SOURCE_EXTENSIONS else "unsupported"


def inspect_archive(
    path: Path, limits: ImportLimits
) -> list[tuple[zipfile.ZipInfo, str]]:
    if path.stat().st_size > limits.archive_bytes:
        raise ImportRejected("archive_bytes", limit=True)
    check_directory_budget(path, limits)
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos:
                raise ImportRejected("empty_archive")
            if len(infos) > limits.entries:
                raise ImportRejected("entries", limit=True)
            result = []
            explicit: set[str] = set()
            nodes: dict[str, tuple[str, bool]] = {}
            declared = sources = 0
            for info in infos:
                name = normalize_path(info.orig_filename)
                key = name.casefold()
                directory = info.is_dir() or info.orig_filename.endswith("\\")
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if (
                    info.flag_bits & (1 | 64)
                    or info.extract_version > 20
                    or kind not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or (kind == stat.S_IFDIR and not directory)
                    or info.compress_type
                    not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                    or (directory and info.file_size != 0)
                ):
                    raise ImportRejected("unsupported_entry")
                if key in explicit:
                    raise ImportRejected("duplicate_path")
                explicit.add(key)
                parts = name.split("/")
                for index in range(1, len(parts) + 1):
                    prefix = "/".join(parts[:index])
                    is_directory = index < len(parts) or directory
                    previous = nodes.get(prefix.casefold())
                    if previous is not None and previous != (prefix, is_directory):
                        raise ImportRejected("path_collision")
                    nodes[prefix.casefold()] = (prefix, is_directory)
                declared += info.file_size
                if declared > limits.declared_bytes:
                    raise ImportRejected("declared_bytes", limit=True)
                if not directory and disposition(name) == "source":
                    sources += 1
                    if (
                        sources > limits.source_files
                        or info.file_size > limits.source_bytes
                    ):
                        raise ImportRejected("source_limit", limit=True)
                # ZipFile 检查本地头、文件名一致性及重叠条目，不使用 extract 的路径修正。
                with archive.open(info):
                    pass
                result.append((info, name))
            return result
    except (
        zipfile.BadZipFile,
        EOFError,
        UnicodeError,
        ValueError,
        NotImplementedError,
    ):
        raise ImportRejected("corrupt_archive") from None


def expanded_chunks(path: Path, info: zipfile.ZipInfo) -> Iterator[bytes]:
    # 直接对有界压缩段计数，避免 ZipExtFile 按伪造 file_size 截断后漏计实际展开量。
    with path.open("rb") as source:
        source.seek(info.header_offset)
        header = source.read(30)
        if len(header) != 30 or header[:4] != b"PK\x03\x04":
            raise ImportRejected("corrupt_header")
        name_size, extra_size = struct.unpack_from("<HH", header, 26)
        source.seek(name_size + extra_size, 1)
        remaining = info.compress_size
        inflater = (
            zlib.decompressobj(-15)
            if info.compress_type == zipfile.ZIP_DEFLATED
            else None
        )
        count = checksum = 0
        while remaining:
            raw = source.read(min(CHUNK_SIZE, remaining))
            if not raw:
                raise ImportRejected("truncated_archive")
            remaining -= len(raw)
            while raw:
                data = inflater.decompress(raw, CHUNK_SIZE) if inflater else raw
                raw = inflater.unconsumed_tail if inflater else b""
                count += len(data)
                checksum = zlib.crc32(data, checksum)
                yield data
            if inflater and inflater.unused_data:
                raise ImportRejected("trailing_compressed_data")
        if (
            (inflater and not inflater.eof)
            or count != info.file_size
            or checksum != info.CRC
        ):
            raise ImportRejected("size_or_crc_mismatch")


def prepare_archive(
    path: Path,
    destination: Path,
    limits: ImportLimits,
    write: Callable[[Path, bytes], None],
    *,
    deadline: float,
) -> PreparedSnapshot:
    infos = inspect_archive(path, limits)
    summary: ImportSummary = {
        "entries": len(infos),
        "accepted": 0,
        "excluded": 0,
        "skipped": 0,
        "rejected": 0,
        "declared_bytes": sum(info.file_size for info, _ in infos),
        "extracted_bytes": 0,
        "reasons": {},
    }
    files: list[PreparedFile] = []
    for info, name in infos:
        category = disposition(name)
        content = bytearray()
        try:
            for data in expanded_chunks(path, info):
                if time.monotonic() >= deadline:
                    raise TimeoutError
                summary["extracted_bytes"] += len(data)
                if summary["extracted_bytes"] > limits.extracted_bytes:
                    raise ImportRejected("extracted_bytes", limit=True)
                if category == "source":
                    if len(content) + len(data) > limits.source_bytes:
                        raise ImportRejected("source_bytes", limit=True)
                    content.extend(data)
        except zlib.error:
            raise ImportRejected("corrupt_compression") from None
        if info.is_dir() or info.orig_filename.endswith("\\"):
            continue
        if category == "source":
            try:
                text = content.decode("utf-8-sig")
                if (
                    any(ord(char) < 32 and char not in "\t\r\n" for char in text)
                    or "\x7f" in text
                ):
                    category = "binary"
            except UnicodeError:
                category = "encoding"
        if category != "source":
            if category == "excluded":
                summary["excluded"] += 1
            else:
                summary["skipped"] += 1
            summary["reasons"][category] = summary["reasons"].get(category, 0) + 1
            continue
        saved = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        if len(saved) > limits.source_bytes:
            raise ImportRejected("source_bytes", limit=True)
        offsets = [0]
        line_count = 1
        for index, byte in enumerate(saved):
            if byte == 10 and index + 1 < len(saved):
                line_count += 1
                if (line_count - 1) % 128 == 0:
                    offsets.append(index + 1)
        identifier = str(uuid.uuid4())
        write(destination / identifier, saved)
        files.append(
            {
                "id": identifier,
                "file_path": name,
                "sha256": hashlib.sha256(saved).hexdigest(),
                "size_bytes": len(saved),
                "line_count": line_count,
                "line_offsets": offsets,
                "encoding": "utf-8",
            }
        )
        summary["accepted"] += 1
    if not files:
        raise ImportRejected("no_supported_source")
    return {"files": files, "summary": summary}
