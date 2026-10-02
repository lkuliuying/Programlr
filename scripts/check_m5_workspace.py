"""验收独立 5177 实例的真实实验、并发、历史及故障；不调用真实模型。"""

import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import check_m4_workspace as learning_workflow

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5177"
EVIDENCE = ROOT / ".runtime/m5-http-verification.json"


class Client:
    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )
        self.token = self.request("/api/v1/csrf/")["csrf_token"]

    def request(
        self,
        path: str,
        body: Any = None,
        *,
        key: str | None = None,
        expected: tuple[int, ...] = (200, 201, 202),
    ) -> dict[str, Any]:
        assert path.startswith("/api/v1/") and not path.startswith("//")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers.update(
                {
                    "Content-Type": "application/json",
                    "Origin": ORIGIN,
                    "X-CSRFToken": self.token,
                    "Idempotency-Key": key or str(uuid.uuid4()),
                }
            )
        request = urllib.request.Request(
            ORIGIN + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        try:
            response = self.opener.open(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            assert response.status in expected, f"HTTP {response.status}: {path}"
            result: dict[str, Any] = json.load(response)
            return result

    def wait(self, job: dict[str, Any]) -> dict[str, Any]:
        deadline = time.monotonic() + 100
        while job["status"] in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(0.2)
            job = self.request(f"/api/v1/jobs/{job['id']}/")
        assert job["status"] in {"succeeded", "failed"}, "任务没有在期限内终结。"
        runs = self.request(f"/api/v1/lab-runs/?job_id={job['id']}")["results"]
        assert len(runs) == 1
        return runs[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labs-only", action="store_true")
    parser.add_argument("--expect-failure", action="store_true")
    parser.add_argument("--verify-history", action="store_true")
    parser.add_argument("--model-double", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    if not (args.labs_only or args.expect_failure or args.verify_history):
        # 复用已验收的真实导入、分析和作答步骤，仅改独立实例地址与证据位置。
        learning_workflow.ORIGIN, learning_workflow.EVIDENCE = ORIGIN, EVIDENCE
        previous_args = sys.argv
        try:
            sys.argv = [
                previous_args[0],
                *(["--model-double"] if args.model_double else []),
            ]
            learning_workflow.main()
        finally:
            sys.argv = previous_args
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    client = Client()
    if args.verify_history:
        for path in evidence["history_paths"]:
            assert client.request(path)["id"] == path.rstrip("/").rsplit("/", 1)[1]
        print(f"重启后历史验证通过：{len(evidence['history_paths'])} 条资源。")
        return
    query = f"analysis_id={evidence['analysis_id']}&endpoint_index={evidence['endpoint_index']}"
    lab = client.request(f"/api/v1/labs/request-validation/?{query}")
    assert lab["applicable"]
    body = {
        "snapshot_id": evidence["snapshot_id"],
        "analysis_id": evidence["analysis_id"],
        "endpoint_index": evidence["endpoint_index"],
        "lab_version": lab["version"],
        "predictions": {
            case["id"]: {
                "status": 201 if case["id"] == "normal" else 400,
                "writes": int(case["id"] == "normal"),
            }
            for case in lab["cases"]
        },
    }
    path, key = "/api/v1/labs/request-validation/runs/", str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=3) as pool:
        submissions = list(
            pool.map(lambda _: Client().request(path, body, key=key), range(3))
        )
    assert len({job["id"] for job in submissions}) == 1
    assert (
        client.request(
            path, {**body, "lab_version": "wrong"}, key=key, expected=(409,)
        )["code"]
        == "IDEMPOTENCY_CONFLICT"
    )
    first = client.wait(submissions[0])
    if args.expect_failure:
        assert (
            first["job"]["status"] == "failed"
            and first["cleanup"]["status"] == "unconfirmed"
        )
        assert first["observations"] == []
        evidence["failure_job"] = first["job"]["id"]
        runs = [first]
    else:
        second_job = client.request(path, body)
        runs = [first, client.wait(second_job)]
        if evidence.get("failure_job"):
            retried = client.request(
                f"/api/v1/jobs/{evidence['failure_job']}/retries/", {}
            )
            assert retried["previous_job_id"] == evidence["failure_job"]
            runs.append(client.wait(retried))
        for run in runs:
            assert run["job"]["status"] == "succeeded", run["job"]["error"]
            assert [item["response"]["status"] for item in run["observations"]] == [
                201,
                400,
                400,
                400,
            ]
            assert [
                item["after_count"] - item["before_count"]
                for item in run["observations"]
            ] == [1, 0, 0, 0]
            assert (
                run["cleanup"]["status"] == "completed"
                and run["cleanup"]["observation"]["record_count"] == 0
            )
        assert len({run["id"] for run in runs}) == len(runs)
    evidence["history_paths"] = list(
        dict.fromkeys(
            [
                *evidence["history_paths"],
                *[f"/api/v1/lab-runs/{run['id']}/" for run in runs],
            ]
        )
    )
    evidence.setdefault("checks", []).append(
        {
            "mode": "unavailable" if args.expect_failure else "success",
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "runs": [
                {
                    "id": run["id"],
                    "status": run["job"]["status"],
                    "observations": len(run["observations"]),
                    "cleanup": run["cleanup"]["status"],
                }
                for run in runs
            ],
        }
    )
    evidence["workspace"] = (
        evidence["workspace"].split("&run=")[0] + f"&run={first['id']}"
    )
    EVIDENCE.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "M5 真实 HTTP 验证通过："
        + (
            "不可用失败与未知清理。"
            if args.expect_failure
            else "观测、隔离、幂等与历史。"
        )
    )
    print(evidence["workspace"])


if __name__ == "__main__":
    main()
