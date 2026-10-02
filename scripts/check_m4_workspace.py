"""验收独立 5176 工作台的固定题与显式启用的模型替身，不调用真实供应商。"""

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

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5176"
EVIDENCE = ROOT / ".runtime/m4-http-verification.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-double", action="store_true")
    parser.add_argument("--verify-history", action="store_true")
    arguments = parser.parse_args()
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
        expected: int | None = None,
    ) -> dict[str, Any]:
        assert path.startswith("/api/v1/")
        data = (
            json.dumps(body).encode()
            if body is not None and not isinstance(body, bytes)
            else body
        )
        headers = {"Accept": "application/json"}
        if body is not None:
            headers.update(
                {
                    "Content-Type": media,
                    "Origin": ORIGIN,
                    "X-CSRFToken": token,
                    "Idempotency-Key": key or str(uuid.uuid4()),
                }
            )
        try:
            with opener.open(
                urllib.request.Request(ORIGIN + path, data=data, headers=headers),
                timeout=15,
            ) as response:
                assert expected is None or response.status == expected
                value: dict[str, Any] = json.load(response)
                return value
        except urllib.error.HTTPError as error:
            assert expected == error.code, f"验收请求失败：{path} HTTP {error.code}"
            with error:
                value = json.load(error)
            return value

    def wait(job: dict[str, Any]) -> dict[str, Any]:
        deadline = time.monotonic() + 90
        while job["status"] in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(0.3)
            job = request(f"/api/v1/jobs/{job['id']}/")
        assert job["status"] == "succeeded", f"任务未成功：{job['id']} {job['status']}"
        return request(job["result_url"])

    if arguments.verify_history:
        stored = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        for path in stored["history_paths"]:
            assert request(path)["id"] == path.rstrip("/").rsplit("/", 1)[1]
        print(f"重启后读取通过：{len(stored['history_paths'])} 条历史资源。")
        return
    token = request("/api/v1/csrf/")["csrf_token"]
    project = request("/api/v1/projects/", {"name": "M4 讲解与练习验收"})
    bundle = json.loads(
        (ROOT / "content/exercises/task-board-create.json").read_text(encoding="utf-8")
    )
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in bundle["files"]:
            output.writestr(path, (ROOT / "examples/task-board" / path).read_bytes())
    boundary = uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="archive"; filename="m4.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode()
        + archive.getvalue()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    snapshot = wait(
        request(
            f"/api/v1/projects/{project['id']}/imports/",
            body,
            media=f"multipart/form-data; boundary={boundary}",
        )
    )
    analysis = wait(
        request(
            f"/api/v1/snapshots/{snapshot['id']}/analyses/",
            {"root_urlconf": "backend/config/urls.py"},
        )
    )
    endpoints = request(f"/api/v1/analyses/{analysis['id']}/endpoints/")["results"]
    endpoint = next(
        item["index"]
        for item in endpoints
        if item["method"] == "POST" and item["path"] == "/api/v1/tasks/"
    )
    query = f"analysis_id={analysis['id']}&endpoint_index={endpoint}"
    exercises = request(f"/api/v1/exercises/?{query}")["results"]
    assert len(exercises) == 3 and all(
        item["applicable"] and "answer" not in item for item in exercises
    )
    assert request("/api/v1/knowledge-cards/")["count"] == 5
    history_paths = [
        f"/api/v1/snapshots/{snapshot['id']}/",
        f"/api/v1/analyses/{analysis['id']}/",
    ]
    for exercise in exercises:
        answer = next(
            item["answer"]
            for item in bundle["exercises"]
            if item["slug"] == exercise["slug"]
        )
        payload = {
            "analysis_id": analysis["id"],
            "snapshot_id": snapshot["id"],
            "endpoint_index": endpoint,
            "exercise_id": exercise["id"],
            "exercise_version": exercise["version"],
            "answer": answer,
            "hint_used": False,
        }
        key = str(uuid.uuid4())
        attempt = request("/api/v1/exercise-attempts/", payload, key=key, expected=201)
        assert (
            attempt["correct"]
            and request("/api/v1/exercise-attempts/", payload, key=key, expected=200)[
                "id"
            ]
            == attempt["id"]
        )
        history_paths.append(f"/api/v1/exercise-attempts/{attempt['id']}/")
    preview_body = {"analysis_id": analysis["id"], "endpoint_index": endpoint}
    if arguments.model_double:
        preview = request("/api/v1/context-previews/", preview_body)
        assert (
            preview["configuration"]["model"] == "m4-test-double"
            and preview["configuration"]["base_url"] == "https://model-test.invalid/v1"
        )
        count_before = request("/api/v1/jobs/?kind=explanation")["count"]
        assert (
            request(
                f"/api/v1/context-previews/{preview['id']}/consents/",
                {"accepted": False},
                expected=400,
            )["code"]
            == "VALIDATION_ERROR"
        )
        assert request("/api/v1/jobs/?kind=explanation")["count"] == count_before
        consent = request(
            f"/api/v1/context-previews/{preview['id']}/consents/", {"accepted": True}
        )
        assert request("/api/v1/jobs/?kind=explanation")["count"] == count_before
        key = str(uuid.uuid4())
        job = request("/api/v1/explanations/", {"consent_id": consent["id"]}, key=key)
        assert (
            request("/api/v1/explanations/", {"consent_id": consent["id"]}, key=key)[
                "id"
            ]
            == job["id"]
        )
        explanation = wait(job)
        assert explanation["model"] == "m4-test-double"
        history_paths.append(f"/api/v1/explanations/{explanation['id']}/")
    else:
        assert (
            request("/api/v1/context-previews/", preview_body, expected=409)["code"]
            == "MODEL_NOT_CONFIGURED"
        )
    evidence = {
        "project_id": project["id"],
        "snapshot_id": snapshot["id"],
        "analysis_id": analysis["id"],
        "endpoint_index": endpoint,
        "history_paths": history_paths,
        "model_double": arguments.model_double,
        "workspace": f"{ORIGIN}/?project={project['id']}&snapshot={snapshot['id']}&analysis={analysis['id']}&endpoint={endpoint}",
    }
    EVIDENCE.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("M4 HTTP 验收通过：三类题、幂等、历史与模型边界。")
    print(evidence["workspace"])


if __name__ == "__main__":
    main()
