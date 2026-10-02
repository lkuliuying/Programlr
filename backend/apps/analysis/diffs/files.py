import difflib
import uuid

from apps.analysis.diffs.types import (
    MAX_FILE_DIFF_BYTES,
    MAX_FILE_LINES,
    ComparisonFailed,
    FileChange,
    FileChangeType,
    FileInput,
)
from apps.analysis.types import SourceRef


def file_change(comparison_id: str, source: FileInput) -> FileChange:
    before, after = source["base_ref"], source["target_ref"]
    kind: FileChangeType = (
        "added"
        if before is None
        else "deleted"
        if after is None
        else "unchanged"
        if source["base_sha256"] == source["target_sha256"]
        else "modified"
    )
    result: FileChange = {
        "id": str(uuid.uuid5(uuid.UUID(comparison_id), source["file_path"])),
        "file_path": source["file_path"],
        "change_type": kind,
        "base_ref": before,
        "target_ref": after,
        "base_sha256": source["base_sha256"],
        "target_sha256": source["target_sha256"],
        "diff": "",
        "base_ranges": [],
        "target_ranges": [],
    }
    if kind == "unchanged":
        return result
    old = (source["base_content"] or "").splitlines(keepends=True)
    new = (source["target_content"] or "").splitlines(keepends=True)
    if max(len(old), len(new)) > MAX_FILE_LINES:
        raise ComparisonFailed("file_line_limit")

    def interval(ref: SourceRef | None, start: int, end: int) -> list[SourceRef]:
        if ref is None:
            return []
        # 插入/删除的空区间保留邻近行作为锚点，不能丢失路由位置变化。
        first = min(start + 1, ref["end_line"])
        last = min(max(first, end), ref["end_line"])
        return [{**ref, "start_line": first, "end_line": last}]

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, old, new, autojunk=False
    ).get_opcodes():
        if tag != "equal":
            result["base_ranges"].extend(interval(before, i1, i2))
            result["target_ranges"].extend(interval(after, j1, j2))
    if not old and not new:
        result["base_ranges"] = [before] if before else []
        result["target_ranges"] = [after] if after else []
    chunks, size = [], 0
    for line in difflib.unified_diff(
        old,
        new,
        fromfile="base/" + source["file_path"],
        tofile="target/" + source["file_path"],
    ):
        rendered = (
            line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
        )
        size += len(rendered.encode("utf-8"))
        if size > MAX_FILE_DIFF_BYTES:
            raise ComparisonFailed("file_diff_limit")
        chunks.append(rendered)
    result["diff"] = "".join(chunks)
    return result
