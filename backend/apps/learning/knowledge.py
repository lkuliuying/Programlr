"""按快照扫描与真实源码范围读取知识，不在读取时创建或补算结果。"""

from bisect import bisect_right
from typing import Any

from django.shortcuts import get_object_or_404

from apps.analysis.models import Analysis, SourceScan
from apps.learning.models import KnowledgeCard
from apps.learning.source_scan import PACKAGE_MAP, STDLIB_CARDS
from apps.projects.models import Snapshot
from common.errors import ApiProblem
from common.resource_state import require_snapshot_available


def contained(reference: dict[str, Any], ranges: list[dict[str, Any]]) -> bool:
    return any(
        reference["snapshot_id"] == str(item["snapshot_id"])
        and reference["file_path"] == item["file_path"]
        and item["start_line"]
        <= reference["start_line"]
        <= reference["end_line"]
        <= item["end_line"]
        for item in ranges
    )


def endpoint_references(analysis: Analysis, index: int) -> list[dict[str, Any]]:
    if not 0 <= index < len(analysis.endpoints):
        raise ApiProblem(400, "VALIDATION_ERROR", "接口序号越界。")
    endpoint = analysis.endpoints[index]
    method_refs = [
        item["source_ref"]
        for item in endpoint["evidence"]
        if item["rule"] == "python.method" and item["source_ref"] is not None
    ]
    refs = list(method_refs)
    for name in ("view", "serializer", "model"):
        symbol = endpoint[name]
        if symbol is None:
            continue
        ref = dict(symbol["source_ref"])
        if name == "view" and method_refs:
            # 整个视图类可能包含其他动作，只补充当前类的声明行。
            ref["end_line"] = ref["start_line"]
        refs.append(ref)
    return refs


def read_scan(snapshot: Snapshot, scan_id: str | None = None) -> SourceScan:
    require_snapshot_available(snapshot)
    scans = SourceScan.objects.filter(snapshot=snapshot, job__status="succeeded")
    scan = get_object_or_404(scans, pk=scan_id) if scan_id else scans.first()
    if scan is None:
        raise ApiProblem(
            409,
            "SOURCE_SCAN_NOT_AVAILABLE",
            "当前快照尚无已完成源码扫描，请显式提交扫描。",
        )
    if not isinstance(scan.result.get("knowledge"), dict):
        raise ApiProblem(
            409, "KNOWLEDGE_NOT_AVAILABLE", "该历史扫描没有知识结果，请显式重新扫描。"
        )
    return scan


def knowledge_hits(scan: SourceScan) -> list[dict[str, Any]]:
    knowledge = scan.result["knowledge"]
    hits = list(knowledge["hits"])
    package_groups: dict[str, list[dict[str, Any]]] = {}
    for package in knowledge["packages"]:
        package_groups.setdefault(package["name"], []).append(package)
    identities = {}
    for name, packages in package_groups.items():
        # 身份以完整扫描的 import 事实为准，筛选使用位置不能改变分类。
        imports = [package for package in packages if package["source_refs"]]
        kinds = {
            (package["kind"], package["distribution"])
            for package in imports or packages
        }
        kind, distribution = next(iter(kinds)) if len(kinds) == 1 else ("unknown", None)
        identities[name] = {"name": name, "kind": kind, "distribution": distribution}
    package_cards = {
        **{slug: (name, "third_party") for name, (_, slug) in PACKAGE_MAP.items()},
        **{slug: (name, "stdlib") for name, slug in STDLIB_CARDS.items()},
        "drf-serializers": ("rest_framework", "third_party"),
        "drf-views": ("rest_framework", "third_party"),
        "django-orm": ("django", "third_party"),
        "django-url-routing": ("django", "third_party"),
    }
    hits = [
        hit
        for hit in hits
        if hit["card_slug"] not in package_cards
        or identities.get(package_cards[hit["card_slug"]][0], {}).get("kind")
        == package_cards[hit["card_slug"]][1]
    ]
    decorator_owners: dict[
        tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]
    ] = {}
    for hit in hits:
        if hit["concept_key"] == "python-decorators" and hit.get("owner_ref"):
            ref = hit["source_ref"]
            key = (ref["snapshot_id"], ref["file_path"])
            decorator_owners.setdefault(key, []).append((ref, hit["owner_ref"]))
    for owners in decorator_owners.values():
        owners.sort(key=lambda item: item[0]["start_line"])
    decorator_starts = {
        key: [ref["start_line"] for ref, _ in owners]
        for key, owners in decorator_owners.items()
    }
    mapped_packages = PACKAGE_MAP.keys() | STDLIB_CARDS.keys()
    for package in knowledge["packages"]:
        identity = identities[package["name"]]
        if package["name"] in mapped_packages and identity["kind"] in {
            "stdlib",
            "third_party",
        }:
            continue
        for rule, refs in (
            ("python.import", package["source_refs"]),
            ("python.import_use", package.get("usage_refs", [])),
        ):
            for ref in refs:
                fact = {
                    "concept_key": "package:" + package["name"],
                    "card_slug": None,
                    "card_version": None,
                    "rule_id": rule,
                    "source_ref": ref,
                    "package": identity,
                }
                if rule == "python.import_use":
                    # 只关联实际装饰器表达式内的使用，不能把同文件顶层 import 注入接口。
                    key = (ref["snapshot_id"], ref["file_path"])
                    owners = decorator_owners.get(key, [])
                    index = (
                        bisect_right(decorator_starts.get(key, []), ref["start_line"])
                        - 1
                    )
                    if index >= 0 and contained(ref, [owners[index][0]]):
                        fact["owner_ref"] = owners[index][1]
                hits.append(fact)
    return sorted(
        hits,
        key=lambda item: (
            item["concept_key"],
            item["source_ref"]["file_path"],
            item["source_ref"]["start_line"],
            item["source_ref"]["end_line"],
        ),
    )


def selected_hits(
    scan: SourceScan,
    *,
    file_path: str | None = None,
    analysis: Analysis | None = None,
    endpoint_index: int | None = None,
    concept_key: str | None = None,
) -> list[dict[str, Any]]:
    ranges = (
        endpoint_references(analysis, endpoint_index)
        if analysis is not None and endpoint_index is not None
        else None
    )
    return [
        hit
        for hit in knowledge_hits(scan)
        if (file_path is None or hit["source_ref"]["file_path"] == file_path)
        and (concept_key is None or hit["concept_key"] == concept_key)
        and (
            ranges is None
            or contained(hit["source_ref"], ranges)
            or (
                hit.get("owner_ref") is not None and contained(hit["owner_ref"], ranges)
            )
        )
    ]


def group_cards(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = {
        (card.slug, card.version): card
        for card in KnowledgeCard.objects.filter(
            slug__in={hit["card_slug"] for hit in hits if hit["card_slug"]}
        )
    }
    groups: dict[str, dict[str, Any]] = {}
    for hit in hits:
        key = hit["concept_key"]
        if key not in groups:
            card = cards.get((hit["card_slug"], hit["card_version"]))
            groups[key] = {
                "concept_key": key,
                "card": card,
                "mapped": card is not None,
                "hit_count": 0,
                "hits": [],
                "package": hit.get("package"),
            }
        group = groups[key]
        group["hit_count"] += 1
        if len(group["hits"]) < 3:
            group["hits"].append(
                {"reason": hit["rule_id"], "source_ref": hit["source_ref"]}
            )
    return list(groups.values())


def preview_cards(
    analysis: Analysis,
    ranges: list[dict[str, Any]],
    *,
    endpoint_index: int | None = None,
) -> list[dict[str, Any]]:
    if not ranges:
        return []
    scan_id = str(analysis.source_scan_id) if analysis.source_scan_id else None
    try:
        scan = read_scan(analysis.snapshot, scan_id)
    except ApiProblem as exc:
        if exc.machine_code in {"SOURCE_SCAN_NOT_AVAILABLE", "KNOWLEDGE_NOT_AVAILABLE"}:
            return []
        raise
    hits = selected_hits(scan, analysis=analysis, endpoint_index=endpoint_index)
    groups = group_cards([hit for hit in hits if contained(hit["source_ref"], ranges)])
    result = []
    for group in groups:
        card = group["card"]
        if card is None:
            continue
        result.append(
            {
                "card_id": str(card.pk),
                "slug": card.slug,
                "version": card.version,
                "content_digest": card.content_digest,
                "title": card.title,
                "body": card.body,
                "source_refs": [hit["source_ref"] for hit in group["hits"]],
            }
        )
    return result[:30]
