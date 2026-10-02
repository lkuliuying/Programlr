"""在显式指定的独立回环实例验收 v0.2 HTTP 主线，不调用模型。"""

import argparse
import http.cookiejar
import io
import json
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    origin = urlsplit(args.origin)
    if (
        origin.scheme != "http"
        or origin.hostname != "127.0.0.1"
        or origin.port is None
        or origin.path
        or origin.query
        or origin.fragment
        or origin.username
    ):
        raise ValueError("只允许显式的 IPv4 回环验收实例。")
    root = Path(__file__).resolve().parents[1]
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )
    token = ""

    def request(
        path: str,
        body: Any = None,
        *,
        media: str = "application/json",
        key: str | None = None,
        expected: tuple[int, ...] = (200, 201, 202),
    ) -> dict[str, Any]:
        assert path.startswith("/api/v1/")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers.update(
                {
                    "Content-Type": media,
                    "Origin": args.origin,
                    "X-CSRFToken": token,
                    "Idempotency-Key": key or str(uuid.uuid4()),
                }
            )
        payload = (
            body
            if isinstance(body, bytes)
            else json.dumps(body).encode()
            if body is not None
            else None
        )
        try:
            response = opener.open(
                urllib.request.Request(
                    args.origin + path, data=payload, headers=headers
                ),
                timeout=15,
            )
        except urllib.error.HTTPError as error:
            response = error
        with response:
            assert response.status in expected, f"HTTP {response.status}：{path}"
            data = json.load(response)
            if not isinstance(data, dict):
                raise TypeError("验收接口返回值必须是 JSON 对象。")
            return data

    def wait(job: dict[str, Any]) -> dict[str, Any]:
        deadline = time.monotonic() + 90
        while job["status"] in {"queued", "running"}:
            if time.monotonic() > deadline:
                raise RuntimeError("验收任务超时；保留历史，不自动重试。")
            time.sleep(0.2)
            job = request(f"/api/v1/jobs/{job['id']}/")
        assert job["status"] == "succeeded", {
            "status": job["status"],
            "error_code": (job.get("error") or {}).get("code"),
        }
        return request(job["result_url"])

    token = request("/api/v1/csrf/")["csrf_token"]
    explanation_jobs_before = request("/api/v1/jobs/?kind=explanation")["count"]
    project = request("/api/v1/projects/", {"name": "v0.2 独立综合验收"})
    example = root / "examples/task-board"
    sources = {
        path.relative_to(example).as_posix(): path.read_bytes()
        for directory in (
            example / "backend/apps/tasks",
            example / "backend/config",
            example / "frontend/src",
        )
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".ts", ".tsx", ".js", ".jsx"}
    }
    sources["v02-candidate.ts"] = (
        b"import axios from 'axios'; const client=axios.create({baseURL:chooseBase()}); export function uncertain(){return client.post('api/v1/tasks/',{});}\n"
    )
    variants = [
        sources,
        {
            **sources,
            "v02-added.ts": b"export function added(){return fetch('/api/v1/tasks/');}\n",
        },
    ]
    serializer = "backend/apps/tasks/api/serializers.py"
    variants[1][serializer] = sources[serializer].replace(
        b"        fields =", "        # v0.2 验收变更\n        fields =".encode()
    )
    snapshots, analyses, timings = [], [], []
    for files in variants:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for path, content in sorted(files.items()):
                output.writestr(path, content)
        boundary = "v02-" + uuid.uuid4().hex
        upload_body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="archive"; filename="v02.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode()
            + archive.getvalue()
            + f"\r\n--{boundary}--\r\n".encode()
        )
        started = time.monotonic()
        snapshot = wait(
            request(
                f"/api/v1/projects/{project['id']}/imports/",
                upload_body,
                media="multipart/form-data; boundary=" + boundary,
            )
        )
        analysis = wait(
            request(
                f"/api/v1/snapshots/{snapshot['id']}/analyses/",
                {"root_urlconf": "backend/config/urls.py"},
            )
        )
        snapshots.append(snapshot)
        analyses.append(analysis)
        timings.append(round(time.monotonic() - started, 3))
    graph_path = f"/api/v1/analyses/{analyses[0]['id']}/graph/"
    graph = request(graph_path)
    edge = next(
        edge for edge in graph["edges"] if edge["relation"] == "candidate_match"
    )
    review_path = f"/api/v1/analyses/{analyses[0]['id']}/relation-reviews/"
    key = str(uuid.uuid4())
    body = {
        "request_id": edge["source_id"],
        "target_id": edge["target_id"],
        "action": "confirm",
        "expected_revision": 0,
    }
    first = request(review_path, body, key=key)
    assert request(review_path, body, key=key)["record"]["id"] == first["record"]["id"]
    assert first["state"]["revision"] == 1
    assert (
        request(review_path, {**body, "action": "exclude"}, expected=(409,))["code"]
        == "RELATION_REVISION_CONFLICT"
    )
    updated = request(graph_path)
    assert graph["nodes"] == updated["nodes"] and graph["edges"] == updated["edges"]
    comparison_path = f"/api/v1/projects/{project['id']}/snapshot-comparisons/"
    binding = {
        "base_snapshot_id": snapshots[0]["id"],
        "target_snapshot_id": snapshots[1]["id"],
        "base_analysis_id": analyses[0]["id"],
        "target_analysis_id": analyses[1]["id"],
    }
    started = time.monotonic()
    key = str(uuid.uuid4())
    job = request(comparison_path, binding, key=key)
    assert request(comparison_path, binding, key=key)["id"] == job["id"]
    comparison = wait(job)
    elapsed = round(time.monotonic() - started, 3)
    assert (
        comparison["comparability"] == "comparable"
        and comparison["summary"]["added"] == 1
        and comparison["summary"]["modified"] == 1
    )
    path = f"/api/v1/snapshot-comparisons/{comparison['id']}/"
    changed = next(
        file
        for file in request(path + "files/")["results"]
        if file["change_type"] == "modified"
    )
    detail = request(path + f"files/{changed['id']}/")
    assert (
        detail["diff"]
        and detail["base_ref"]["snapshot_id"] == snapshots[0]["id"]
        and detail["target_ref"]["snapshot_id"] == snapshots[1]["id"]
    )
    impact_start = time.monotonic()
    impact = request(path + "impact/")
    impact_elapsed = round(time.monotonic() - impact_start, 3)
    assert all(
        impact[side]["available"] and impact[side]["impact"]["results"]
        for side in ("base", "target")
    )
    opted = request(path + "impact/?include_candidates=true")
    assert any(item["via_candidate"] for item in opted["target"]["impact"]["results"])
    assert request("/api/v1/jobs/?kind=explanation")["count"] == explanation_jobs_before
    evidence = {
        "project_id": project["id"],
        "snapshots": [x["id"] for x in snapshots],
        "analyses": [x["id"] for x in analyses],
        "comparison_id": comparison["id"],
        "change_id": changed["id"],
        "request_id": edge["source_id"],
        "target_id": edge["target_id"],
        "summary": comparison["summary"],
        "files": [x["summary"]["accepted"] for x in snapshots],
        "bytes": [x["summary"]["extracted_bytes"] for x in snapshots],
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "import_and_analysis_seconds": timings,
        "comparison_seconds": elapsed,
        "impact_seconds": impact_elapsed,
        "impact_truncated": [
            impact[side]["impact"]["truncated"] for side in ("base", "target")
        ],
        "workspace": f"{args.origin}/?project={project['id']}&snapshot={snapshots[0]['id']}&analysis={analyses[0]['id']}&node={edge['source_id']}&comparison={comparison['id']}&change={changed['id']}",
    }
    args.evidence.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "v0.2 HTTP 主线通过：导入、双侧分析、候选确认、冲突、对比、路径和候选开关；模型调用为零。"
    )
    print(evidence["workspace"])


if __name__ == "__main__":
    main()
