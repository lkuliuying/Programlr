"""只读取历史讲解的引用，不准备模型配置或发送范围。"""

import hashlib
import json
import uuid

from apps.analysis.diffs.types import ComparisonFailed, SavedEvidence
from apps.analysis.types import SourceRef
from apps.explanations.adapter import ModelFailure
from apps.explanations.models import Explanation
from apps.explanations.validation import validate_content


def read_saved_evidence(
    snapshot_id: uuid.UUID, analysis_id: uuid.UUID | None, line_counts: dict[str, int]
) -> list[SavedEvidence]:
    records = Explanation.objects.filter(preview__snapshot_id=snapshot_id)
    if analysis_id:
        records = records.filter(preview__analysis_id=analysis_id)
    values = list(
        records.values(
            "id",
            "content",
            "preview_id",
            "preview__analysis_id",
            "preview__endpoint_index",
            "preview__payload__snippets",
        )[:201]
    )
    if len(values) > 200:
        raise ComparisonFailed("evidence_count_limit")
    results: list[SavedEvidence] = []
    for record in values:
        refs: list[SourceRef] = []
        valid = True
        try:
            snippets = record["preview__payload__snippets"]
            if not isinstance(snippets, list) or not snippets:
                raise ValueError
            for snippet in snippets:
                if (
                    not isinstance(snippet, dict)
                    or not isinstance(snippet.get("content"), str)
                    or snippet.get("sha256")
                    != hashlib.sha256(snippet["content"].encode()).hexdigest()
                ):
                    raise ValueError
            content = validate_content(json.dumps(record["content"]), snippets)
            unique = {}
            for claims in content.values():
                for claim in claims:
                    for ref in claim["source_refs"]:
                        if (
                            ref["snapshot_id"] != str(snapshot_id)
                            or ref["file_path"] not in line_counts
                            or not 1
                            <= ref["start_line"]
                            <= ref["end_line"]
                            <= line_counts[ref["file_path"]]
                        ):
                            raise ValueError
                        unique[json.dumps(ref, sort_keys=True)] = ref
            refs = [unique[key] for key in sorted(unique)]
        except (ModelFailure, ValueError, TypeError, KeyError, AttributeError):
            valid = False
        results.append(
            {
                "explanation_id": str(record["id"]),
                "preview_id": str(record["preview_id"]),
                "analysis_id": str(record["preview__analysis_id"]),
                "endpoint_index": record["preview__endpoint_index"],
                "source_refs": refs,
                "valid": valid,
            }
        )
    return results
