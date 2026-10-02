"""在明确指定的独立回环实例验证 v0.3 学习与真实 Worker 实验，不调用模型。"""

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


def main() -> int:
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
        raise ValueError("只接受显式 IPv4 回环验收入口。")
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
        if not path.startswith("/api/v1/") or "://" in path:
            raise ValueError("验收资源路径无效。")
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
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            if response.status not in expected:
                raise RuntimeError(f"验收 HTTP {response.status}：{path}")
            value: dict[str, Any] = json.load(response)
            if not isinstance(value, dict):
                raise TypeError("验收响应必须是 JSON 对象。")
            return value

    def wait(job: dict[str, Any]) -> dict[str, Any]:
        deadline = time.monotonic() + 90
        while job["status"] in {"queued", "running"}:
            if time.monotonic() >= deadline:
                raise RuntimeError("验收任务等待超时，历史保留，不自动重试。")
            time.sleep(0.2)
            job = request(f"/api/v1/jobs/{job['id']}/")
        if job["status"] != "succeeded":
            raise RuntimeError(
                "验收任务失败：" + (job.get("error") or {}).get("code", "UNKNOWN")
            )
        return request(job["result_url"])

    token = request("/api/v1/csrf/")["csrf_token"]
    before_models = request("/api/v1/jobs/?kind=explanation")["count"]
    project = request("/api/v1/projects/", {"name": "v0.3 独立学习验收"})
    bundle = json.loads(
        (root / "content/exercises/task-board-create.json").read_text(encoding="utf-8")
    )
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name in bundle["files"]:
            output.writestr(name, (root / "examples/task-board" / name).read_bytes())
    boundary = "v03-" + uuid.uuid4().hex
    upload = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="archive"; filename="v03-example.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode()
        + archive.getvalue()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    snapshot = wait(
        request(
            f"/api/v1/projects/{project['id']}/imports/",
            upload,
            media="multipart/form-data; boundary=" + boundary,
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
    curriculum = request("/api/v1/knowledge-curricula/")["results"][0]
    path_url = f"/api/v1/learning-paths/?{query}&curriculum_id={curriculum['id']}"
    path = request(path_url)
    assert path["applicable"] and set(path["order"]) == {
        "http",
        "validation",
        "serialization",
        "orm",
        "react-state",
    }
    assert request(path_url) == path
    for edge in curriculum["definition"]["edges"]:
        if edge["dependent"] in path["order"]:
            assert path["order"].index(edge["prerequisite"]) < path["order"].index(
                edge["dependent"]
            )
    exercises = request("/api/v1/exercises/?" + query)["results"]
    exercise = next(item for item in exercises if item["kind"] == "flow_order")
    expected = next(
        item for item in bundle["exercises"] if item["slug"] == exercise["slug"]
    )
    values = {
        "snapshot_id": snapshot["id"],
        "analysis_id": analysis["id"],
        "endpoint_index": endpoint,
        "exercise_id": exercise["id"],
        "exercise_version": exercise["version"],
        "answer": expected["answer"],
        "hint_used": True,
    }
    key = str(uuid.uuid4())
    attempt = request("/api/v1/exercise-attempts/", values, key=key)
    assert (
        attempt["correct"]
        and attempt["hint_used"]
        and attempt["previous_attempt_id"] is None
    )
    assert (
        request(
            "/api/v1/exercise-attempts/",
            {**values, "previous_attempt_id": None},
            key=key,
        )["id"]
        == attempt["id"]
    )
    review_key, review_body = (
        str(uuid.uuid4()),
        {
            "attempt_id": attempt["id"],
            "judgement": "revisit",
            "note": "合成 HTTP 验收笔记",
        },
    )
    review = request("/api/v1/attempt-reviews/", review_body, key=review_key)
    assert (
        request("/api/v1/attempt-reviews/", review_body, key=review_key)["id"]
        == review["id"]
    )
    assert (
        request(
            "/api/v1/attempt-reviews/",
            {**review_body, "judgement": "understood"},
            key=review_key,
            expected=(409,),
        )["code"]
        == "IDEMPOTENCY_CONFLICT"
    )
    newer = request(
        "/api/v1/exercise-attempts/",
        {**values, "previous_attempt_id": attempt["id"], "hint_used": False},
    )
    assert (
        newer["id"] != attempt["id"]
        and newer["previous_attempt_id"] == attempt["id"]
        and not newer["hint_used"]
    )
    assert request(f"/api/v1/exercise-attempts/{attempt['id']}/")["hint_used"]
    assert request(f"/api/v1/attempt-reviews/?attempt_id={attempt['id']}")["count"] == 1
    results, timings = {}, {}
    for lab in request("/api/v1/system-labs/?" + query)["results"]:
        values = {
            "snapshot_id": snapshot["id"],
            "analysis_id": analysis["id"],
            "endpoint_index": endpoint,
            "lab_version": lab["version"],
            "predictions": {
                "first": lab["id"] == "subprocess-lifecycle",
                "second": lab["id"] == "container-network",
            },
        }
        key = str(uuid.uuid4())
        started = time.monotonic()
        submitted = request(f"/api/v1/system-labs/{lab['id']}/runs/", values, key=key)
        assert (
            request(f"/api/v1/system-labs/{lab['id']}/runs/", values, key=key)["id"]
            == submitted["id"]
        )
        run = wait(submitted)
        timings[lab["id"]] = round(time.monotonic() - started, 3)
        assert (
            run["cleanup"]["status"] == "completed"
            and len(run["observations"]) == 2
            and all(item["reaped"] for item in run["observations"])
        )
        if lab["id"] == "container-network":
            assert (
                not run["observations"][0]["connected"]
                and run["observations"][1]["connected"]
            )
        else:
            assert (
                run["observations"][0]["return_code"] == 0
                and run["observations"][1]["return_code"] == -9
                and run["observations"][1]["timed_out"]
            )
        results[lab["id"]] = {
            "run_id": run["id"],
            "job_id": run["job"]["id"],
            "observation_count": len(run["observations"]),
            "all_reaped": True,
        }
    assert request("/api/v1/jobs/?kind=explanation")["count"] == before_models
    evidence = {
        "origin": args.origin,
        "project_id": project["id"],
        "snapshot_id": snapshot["id"],
        "analysis_id": analysis["id"],
        "endpoint_index": endpoint,
        "curriculum_id": curriculum["id"],
        "attempt_id": attempt["id"],
        "reattempt_id": newer["id"],
        "review_id": review["id"],
        "learning_order": path["order"],
        "experiments": results,
        "timings_seconds": timings,
        "model_calls": 0,
        "workspace_url": f"{args.origin}/?project={project['id']}&snapshot={snapshot['id']}&analysis={analysis['id']}&endpoint={endpoint}&attempt={attempt['id']}&curriculum={curriculum['id']}&goal=create-task",
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("v0.3 真实 HTTP/Worker 学习、复习、重新作答及两项系统实验通过；无模型调用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
