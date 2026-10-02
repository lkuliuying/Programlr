"""仅对独立回环验收实例检查导入、前端关联和快照隔离。"""

import argparse
import http.cookiejar
import io
import json
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", type=uuid.UUID)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    origin = "http://127.0.0.1:5175"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )
    token = None

    def request(
        path: str,
        body: bytes | None = None,
        media: str = "application/json",
        key: str | None = None,
    ) -> dict:
        assert path.startswith("/api/v1/")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers.update(
                {
                    "Content-Type": media,
                    "Origin": origin,
                    "X-CSRFToken": token,
                    "Idempotency-Key": key or str(uuid.uuid4()),
                }
            )
        with opener.open(
            urllib.request.Request(origin + path, data=body, headers=headers),
            timeout=10,
        ) as response:
            return json.load(response)

    def wait(job: dict) -> dict:
        deadline = time.monotonic() + 90
        while job["status"] in {"queued", "running"}:
            if time.monotonic() >= deadline:
                raise AssertionError("验收任务超时，保留任务记录供核对。")
            time.sleep(0.5)
            job = request(f"/api/v1/jobs/{job['id']}/")
        assert job["status"] == "succeeded", {
            "status": job["status"],
            "code": (job.get("error") or {}).get("code"),
        }
        return request(job["result_url"])

    token = request("/api/v1/csrf/")["csrf_token"]
    if arguments.project_id:
        project = request(f"/api/v1/projects/{arguments.project_id}/")
    else:
        project = request(
            "/api/v1/projects/", json.dumps({"name": "M3 HTTP 验收"}).encode()
        )
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        example = root / "examples/task-board"
        for directory in (
            example / "backend/apps/tasks",
            example / "backend/config",
            example / "frontend/src",
        ):
            for file in sorted(directory.rglob("*")):
                if file.is_file() and file.suffix in {
                    ".py",
                    ".js",
                    ".jsx",
                    ".ts",
                    ".tsx",
                }:
                    output.write(file, file.relative_to(example).as_posix())
        output.writestr(
            "m3-candidates.ts",
            "import axios from 'axios'; const client=axios.create({baseURL:chooseBase()}); client.post('api/v1/tasks/',{}); fetch(dynamicPath);\n",
        )
        output.writestr("m3-broken.ts", "function broken( {\n")
        output.writestr("empty_urls.py", "urlpatterns=[]\n")
    boundary = "m3-verification-" + uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="archive"; filename="m3-verification.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode()
        + archive.getvalue()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    import_key = str(uuid.uuid4())
    job = request(
        f"/api/v1/projects/{project['id']}/imports/",
        body,
        f"multipart/form-data; boundary={boundary}",
        import_key,
    )
    assert (
        request(
            f"/api/v1/projects/{project['id']}/imports/",
            body,
            f"multipart/form-data; boundary={boundary}",
            import_key,
        )["id"]
        == job["id"]
    )
    snapshot = wait(job)
    analysis_key = str(uuid.uuid4())
    path = f"/api/v1/snapshots/{snapshot['id']}/analyses/"
    body = json.dumps({"root_urlconf": "backend/config/urls.py"}).encode()
    job = request(path, body, key=analysis_key)
    assert request(path, body, key=analysis_key)["id"] == job["id"]
    analysis = wait(job)
    assert analysis["snapshot_id"] == snapshot["id"]
    assert (
        analysis["frontend"]["candidate"] > 0 and analysis["frontend"]["unmatched"] > 0
    )
    assert analysis["frontend"]["coverage"]["syntax_failed_files"] == 1
    path = f"/api/v1/analyses/{analysis['id']}/"
    endpoints = request(path + "endpoints/")["results"]
    target = next(
        endpoint
        for endpoint in endpoints
        if endpoint["method"] == "POST" and endpoint["path"] == "/api/v1/tasks/"
    )
    graph = request(path + f"graph/?endpoint_index={target['index']}")
    assert {
        "handleSubmit",
        "mutationFn",
        "createTask",
        "TaskListCreateView",
        "TaskSerializer",
        "Task",
    } <= {node["name"] for node in graph["nodes"]}
    assert sum(node["kind"] == "endpoint" for node in graph["nodes"]) == 1
    assert {"candidate_match", "method_path_match", "callback_binding"} <= {
        edge["relation"] for edge in graph["edges"]
    }
    files = request(f"/api/v1/snapshots/{snapshot['id']}/files/?page_size=100")[
        "results"
    ]
    by_path = {file["file_path"]: file for file in files}
    for node in graph["nodes"]:
        ref = node["source_ref"]
        if ref:
            assert ref["snapshot_id"] == snapshot["id"]
            assert (
                1
                <= ref["start_line"]
                <= ref["end_line"]
                <= by_path[ref["file_path"]]["line_count"]
            )
    model = next(node for node in graph["nodes"] if node["kind"] == "model")
    ref = model["source_ref"]
    source = request(
        f"/api/v1/snapshots/{snapshot['id']}/files/{by_path[ref['file_path']]['id']}/content/?start_line={ref['start_line']}&end_line={ref['end_line']}"
    )
    assert "class Task(models.Model)" in source["content"]
    report = {
        "project_id": project["id"],
        "snapshot_id": snapshot["id"],
        "analysis_id": analysis["id"],
        "endpoint_index": target["index"],
        "confirmed": analysis["frontend"]["confirmed"],
        "candidate": analysis["frontend"]["candidate"],
        "unmatched": analysis["frontend"]["unmatched"],
        "syntax_failed_files": 1,
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "idempotency": "passed",
        "source_ownership": "passed",
    }
    output = root / ".runtime/m3-http-verification.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
