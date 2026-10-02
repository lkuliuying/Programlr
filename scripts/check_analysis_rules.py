"""评估分离的合成样例；保留旧规则结果，不将有限样例当成容量或真实准确率。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

if TYPE_CHECKING:
    from apps.analysis.types import Source

SNAPSHOT = "00000000-0000-0000-0000-000000000001"
SERIALIZERS = (
    "from rest_framework.serializers import Serializer\n"
    "class ItemSerializer(Serializer):\n    pass\n"
    "class AlternateSerializer(Serializer):\n    pass\n"
)


def backend_sources(case: dict[str, Any]) -> list[Source]:
    from apps.analysis.types import Source

    if case["kind"] == "router":
        return [
            Source("serializers.py", SERIALIZERS),
            Source("views.py", case["view_source"]),
            Source("router_urls.py", case["router_source"]),
            Source(
                "urls.py",
                "from django.urls import include, path\n"
                "urlpatterns = [path('api/', include('router_urls'))]\n",
            ),
        ]
    route = "path('api/items/', Items.as_view())"
    routes = f"{route}, {route}" if case.get("duplicate_routes") else route
    return [
        Source("serializers.py", SERIALIZERS),
        Source(
            "urls.py",
            "from django.urls import path\n"
            "from rest_framework.generics import ListAPIView\n"
            "from serializers import ItemSerializer\n"
            "class Items(ListAPIView):\n    serializer_class = ItemSerializer\n"
            f"urlpatterns = [{routes}]\n",
        ),
    ]


def evaluate(node: str) -> dict[str, Any]:
    from apps.analysis.associations import associate
    from apps.analysis.parser import analyze
    from apps.analysis.types import RULE_VERSION

    groups: dict[str, Any] = {}
    frontend_version = None
    for group in ("development", "evaluation"):
        path = ROOT / f"testdata/analysis/v02-{group}.json"
        dataset = json.loads(path.read_text(encoding="utf-8"))
        results = []
        totals = {
            name: 0
            for name in (
                "expected_supported_items",
                "correct_recognitions",
                "false_associations",
                "missed_items",
                "candidates",
                "unsupported_cases",
                "fully_matching_cases",
            )
        }
        for case in dataset["cases"]:
            parsed = analyze(SNAPSHOT, backend_sources(case), "urls.py")
            actual_endpoints = sorted(
                [
                    e["method"],
                    e["path"],
                    e["action"],
                    e["serializer"]["name"] if e["serializer"] else None,
                ]
                for e in parsed["endpoints"]
                if e["method"] not in {"HEAD", "OPTIONS"}
            )
            expected = sorted(case.get("expected_endpoints", []))
            requests = []
            if case["kind"] == "frontend":
                payload = {
                    "protocol_version": "typescript-analysis/1.0.0",
                    "snapshot_id": SNAPSHOT,
                    "sources": [
                        {"file_path": p, "content": c}
                        for p, c in case["frontend_sources"].items()
                    ],
                }
                process = subprocess.run(
                    [node, str(ROOT / "analyzers/typescript/dist/cli.js")],
                    input=json.dumps(payload),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=60,
                    check=True,
                )
                frontend = json.loads(process.stdout)
                frontend_version = frontend["rule_version"]
                linked = associate(frontend, parsed["endpoints"])
                requests = [
                    [r["method"], r["path"], r["resolution"], m["status"]]
                    for r, m in zip(
                        frontend["requests"], linked["matches"], strict=True
                    )
                ]
                actual = {tuple(r) for r in requests}
                expected_items = {tuple(r) for r in case["expected_requests"]}
                totals["candidates"] += sum(r[-1] == "candidate" for r in requests)
                totals["false_associations"] += sum(
                    r[-1] == "confirmed" and tuple(r) not in expected_items
                    for r in requests
                )
                recognized = len(actual & expected_items) if case["supported"] else 0
                count = len(expected_items) if case["supported"] else 0
                matching = requests == case["expected_requests"]
            else:
                actual, expected_items = (
                    set(map(tuple, actual_endpoints)),
                    set(map(tuple, expected)),
                )
                recognized, count = len(actual & expected_items), len(expected_items)
                totals["false_associations"] += len(actual - expected_items)
                matching = actual_endpoints == expected
            totals["expected_supported_items"] += count
            totals["correct_recognitions"] += recognized
            totals["missed_items"] += count - recognized
            totals["unsupported_cases"] += not case["supported"]
            totals["fully_matching_cases"] += matching
            results.append(
                {
                    "case": case["id"],
                    "supported": case["supported"],
                    "matches_expectation": matching,
                    "endpoints": actual_endpoints if case["kind"] == "router" else None,
                    "requests": requests,
                    "diagnostics": sorted({d["code"] for d in parsed["diagnostics"]}),
                }
            )
        groups[group] = {
            "dataset_version": dataset["dataset_version"],
            "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "case_count": len(results),
            "totals": totals,
            "cases": results,
        }
    return {
        "backend_rule_version": RULE_VERSION,
        "frontend_rule_version": frontend_version,
        "scope": "合成有限集；识别分母与不支持项分开，无容量或真实项目准确率承诺",
        "groups": groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--node",
        default=str(ROOT / ".runtime/tools/node-v24.21.0-win-x64/node.exe")
        if os.name == "nt"
        else "node",
    )
    parser.add_argument("--capture-baseline", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = evaluate(args.node)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.capture_baseline:
        with args.capture_baseline.open("x", encoding="utf-8") as stream:
            stream.write(serialized)
    if args.report:
        args.report.write_text(serialized, encoding="utf-8")
    print(
        json.dumps(
            {name: group["totals"] for name, group in report["groups"].items()},
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.capture_baseline:
        return 0
    return (
        0
        if all(
            group["totals"]["fully_matching_cases"] == group["case_count"]
            for group in report["groups"].values()
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
