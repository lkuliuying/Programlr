from collections.abc import Mapping

from apps.analysis.diffs.files import file_change
from apps.analysis.diffs.semantics import compare_semantics
from apps.analysis.diffs.types import (
    COMPARISON_VERSION,
    MAX_FILES,
    ComparisonData,
    ComparisonFailed,
    ComparisonInput,
    ExplanationApplicability,
    ReferenceApplicability,
)


def compare(payload: ComparisonInput) -> ComparisonData:
    if len(payload["files"]) > MAX_FILES:
        raise ComparisonFailed("file_count_limit")
    files = [
        file_change(payload["comparison_id"], source) for source in payload["files"]
    ]
    result: ComparisonData = {
        "comparison_version": COMPARISON_VERSION,
        "summary": {"added": 0, "deleted": 0, "modified": 0, "unchanged": 0},
        "files": files,
        "comparability": "files_only",
        "comparison_notes": [],
        "base_version": payload["base_analysis"]["version"]
        if payload["base_analysis"]
        else None,
        "target_version": payload["target_analysis"]["version"]
        if payload["target_analysis"]
        else None,
        "interfaces": [],
        "relations": [],
        "evidence": [],
    }
    for file in files:
        result["summary"][file["change_type"]] += 1
    base, target = payload["base_analysis"], payload["target_analysis"]
    if base and target:
        relevant = (
            "root_urlconf",
            "rule_version",
            "graph_version",
            "frontend_rule_version",
            "association_rule_version",
        )
        versions: tuple[Mapping[str, object], Mapping[str, object]] = (
            base["version"],
            target["version"],
        )
        differing = [
            field for field in relevant if versions[0][field] != versions[1][field]
        ]
        if differing or base["graph"] is None or target["graph"] is None:
            result["comparability"] = "incomparable"
            result["comparison_notes"] = (
                ["分析入口或规则版本不同：" + "、".join(differing)]
                if differing
                else ["至少一侧缺少可用关系图。"]
            )
        else:
            result["comparability"] = "comparable"
            result["interfaces"], result["relations"] = compare_semantics(base, target)
            if base["version"]["frontend_rule_version"] is None:
                result["comparison_notes"].append(
                    "两侧均为未分析前端的历史结果，关联对比仅覆盖后端。"
                )
    else:
        result["comparison_notes"].append(
            "未绑定成对分析，仅提供文件差异与旧证据适用性。"
        )
    by_path = {file["file_path"]: file for file in files}
    for saved in payload["evidence"]:
        entry: ExplanationApplicability = {
            "explanation_id": saved["explanation_id"],
            "preview_id": saved["preview_id"],
            "analysis_id": saved["analysis_id"],
            "endpoint_index": saved["endpoint_index"],
            "references": [],
            "warning": None
            if saved["valid"]
            else "旧证据结构无法核验，适用性无法判断。",
        }
        for ref in saved["source_refs"]:
            referenced_file = by_path.get(ref["file_path"])
            applicability: ReferenceApplicability = {
                "source_ref": ref,
                "target_ref": None,
                "applicability": "unknown",
            }
            if (
                saved["valid"]
                and referenced_file
                and referenced_file["base_ref"]
                and ref["snapshot_id"] == payload["base_snapshot_id"]
                and ref["end_line"] <= referenced_file["base_ref"]["end_line"]
            ):
                applicability["applicability"] = (
                    "deleted"
                    if referenced_file["target_ref"] is None
                    else "unchanged"
                    if referenced_file["change_type"] == "unchanged"
                    else "review"
                )
                if applicability["applicability"] == "unchanged":
                    applicability["target_ref"] = {
                        **ref,
                        "snapshot_id": payload["target_snapshot_id"],
                    }
            entry["references"].append(applicability)
        result["evidence"].append(entry)
    result["comparison_notes"].append(
        "引用文件未变不等于讲解语义已验证；原引用始终属于基准快照。"
    )
    return result
