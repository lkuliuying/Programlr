"""v1.0 的无敏感合成规模评估及明确口径的资源读数。"""

import http.cookiejar
import io
import json
import math
import statistics
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5181"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise RuntimeError("验收入口发生重定向，已停止请求。")


class Client:
    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            NoRedirect(),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )
        self.token = ""
        self.token = self.request("/api/v1/csrf/")["csrf_token"]

    def request(
        self,
        path: str,
        body: Any = None,
        *,
        media: str = "application/json",
        key: str | None = None,
        expected: tuple[int, ...] = (200, 201, 202),
    ) -> dict[str, Any]:
        if not path.startswith("/api/v1/") or "\\" in path or "#" in path:
            raise ValueError("验收只允许工作台内的 API 地址。")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers.update(
                {
                    "Content-Type": media,
                    "Origin": ORIGIN,
                    "X-CSRFToken": self.token,
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
            response = self.opener.open(
                urllib.request.Request(ORIGIN + path, data=payload, headers=headers),
                timeout=15,
            )
        except urllib.error.HTTPError as error:
            response = error
        with response:
            if response.status not in expected:
                raise RuntimeError(f"验收 API 返回 HTTP {response.status}。")
            raw = response.read(32 * 1024 * 1024 + 1)
        if len(raw) > 32 * 1024 * 1024:
            raise RuntimeError("验收读取超限。")
        result: Any = json.loads(raw)
        if not isinstance(result, dict):
            raise RuntimeError("验收 API 返回形状无效。")
        return dict(result)

    def wait(self, job: dict[str, Any]) -> dict[str, Any]:
        deadline = time.monotonic() + 100
        while job["status"] in {"queued", "running"}:
            if time.monotonic() >= deadline:
                raise RuntimeError("验收任务等待超时；保留记录，不自动重试。")
            time.sleep(0.2)
            job = self.request(f"/api/v1/jobs/{job['id']}/")
        if job["status"] != "succeeded":
            raise RuntimeError("验收任务未成功；请查询原记录，不自动重试。")
        return self.request(job["result_url"])


def workload(file_count: int) -> tuple[bytes, dict[str, Any]]:
    bundle = json.loads(
        (ROOT / "content/exercises/task-board-create.json").read_text(encoding="utf-8")
    )
    files = {
        name: (ROOT / "examples/task-board" / name).read_bytes()
        for name in bundle["files"]
    }
    if not len(files) <= file_count <= 500:
        raise ValueError("合成评估只支持标准样例到 500 文件的固定规模。")
    for index in range(file_count - len(files)):
        files[f"backend/synthetic/module_{index:04d}.py"] = (
            f"def normalize_title_{index}(value: str) -> str:\n"
            "    return value.strip()\n"
        ).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, source in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source)
    value = output.getvalue()
    return value, {
        "files": len(files),
        "source_bytes": sum(map(len, files.values())),
        "source_lines": sum(source.count(b"\n") for source in files.values()),
        "archive_bytes": len(value),
        "synthetic": file_count > len(bundle["files"]),
        "scope": "标准源码加独立小模块；不代表复杂真实项目或容量上限",
    }


def timing_summary(samples: list[float]) -> dict[str, Any]:
    if not samples or any(not math.isfinite(item) or item < 0 for item in samples):
        raise ValueError("耗时样本必须非空、有限且非负。")
    return {
        "samples_seconds": [round(item, 4) for item in samples],
        "min_seconds": round(min(samples), 4),
        "median_seconds": round(statistics.median(samples), 4),
        "max_seconds": round(max(samples), 4),
        "sample_count": len(samples),
    }


def read_memory_metrics(raw: str) -> dict[str, Any]:
    values = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)

    def number(key: str) -> int | None:
        value = values.get(key, "")
        return int(value) if value.isdecimal() else None

    v2_peak, v1_peak = number("v2_peak"), number("v1_peak")
    version = "v2" if v2_peak is not None else "v1" if v1_peak is not None else None
    return {
        "cgroup_version": version,
        "memory_peak_bytes": v2_peak if v2_peak is not None else v1_peak,
        "memory_current_bytes": number("v2_current")
        if version == "v2"
        else number("v1_current")
        if version == "v1"
        else None,
        "memory_limit_bytes": number("v2_limit")
        if version == "v2"
        else number("v1_limit")
        if version == "v1"
        else None,
        "pids_current": number("pids_current"),
        "peak_scope": "容器创建至本次读数的内核峰值，包含启动和全部验收",
        "unavailable": version is None,
    }


def learning_checks(evidence: dict[str, Any]) -> dict[str, Any]:
    client = Client()
    expected_cards = {
        (item["slug"], item["version"])
        for source in (ROOT / "content/knowledge").glob("*.json")
        for item in json.loads(source.read_text(encoding="utf-8"))
    }
    cards = client.request("/api/v1/knowledge-cards/?page_size=100")
    if (
        cards["count"] != len(expected_cards)
        or {(item["slug"], item["version"]) for item in cards["results"]}
        != expected_cards
    ):
        raise RuntimeError("已发布知识卡片与本版内容清单不一致。")
    query = f"analysis_id={evidence['analysis_id']}&endpoint_index={evidence['endpoint_index']}"
    exercises = client.request("/api/v1/exercises/?" + query)["results"]
    bundle = json.loads(
        (ROOT / "content/exercises/task-board-create.json").read_text(encoding="utf-8")
    )
    if {item["slug"] for item in exercises} != {
        item["slug"] for item in bundle["exercises"]
    }:
        raise RuntimeError("三类固定题目与本版内容清单不一致。")
    history = [
        f"/api/v1/snapshots/{evidence['snapshot_id']}/",
        f"/api/v1/analyses/{evidence['analysis_id']}/",
    ]
    for exercise in exercises:
        if not exercise["applicable"] or "answer" in exercise:
            raise RuntimeError("题目适用性或答案保密边界不一致。")
        definition = next(
            item for item in bundle["exercises"] if item["slug"] == exercise["slug"]
        )
        body = {
            "analysis_id": evidence["analysis_id"],
            "snapshot_id": evidence["snapshot_id"],
            "endpoint_index": evidence["endpoint_index"],
            "exercise_id": exercise["id"],
            "exercise_version": exercise["version"],
            "answer": definition["answer"],
            "hint_used": False,
        }
        key = str(uuid.uuid4())
        attempt = client.request("/api/v1/exercise-attempts/", body, key=key)
        if (
            not attempt["correct"]
            or client.request("/api/v1/exercise-attempts/", body, key=key)["id"]
            != attempt["id"]
        ):
            raise RuntimeError("固定题正确性或同键恢复验证失败。")
        history.append(f"/api/v1/exercise-attempts/{attempt['id']}/")
    before = client.request("/api/v1/jobs/?kind=explanation")["count"]
    disabled = client.request(
        "/api/v1/context-previews/",
        {
            "analysis_id": evidence["analysis_id"],
            "endpoint_index": evidence["endpoint_index"],
        },
        expected=(409,),
    )
    if (
        disabled["code"] != "MODEL_NOT_CONFIGURED"
        or client.request("/api/v1/jobs/?kind=explanation")["count"] != before
    ):
        raise RuntimeError("关闭模型的边界未通过。")
    return {
        "project_id": evidence["project_id"],
        "snapshot_id": evidence["snapshot_id"],
        "analysis_id": evidence["analysis_id"],
        "endpoint_index": evidence["endpoint_index"],
        "history_paths": history,
        "model_double": False,
        "workspace": evidence["workspace_url"],
        "knowledge_cards_checked": len(expected_cards),
        "exercise_kinds_checked": len(exercises),
    }


MEMORY_COMMAND = """
for item in \
v2_peak:/sys/fs/cgroup/memory.peak \
v2_current:/sys/fs/cgroup/memory.current \
v2_limit:/sys/fs/cgroup/memory.max \
v1_peak:/sys/fs/cgroup/memory/memory.max_usage_in_bytes \
v1_current:/sys/fs/cgroup/memory/memory.usage_in_bytes \
v1_limit:/sys/fs/cgroup/memory/memory.limit_in_bytes \
pids_current:/sys/fs/cgroup/pids.current \
pids_current:/sys/fs/cgroup/pids/pids.current; do
  key=${item%%:*}; file=${item#*:}
  if [ -r "$file" ]; then printf '%s=' "$key"; cat "$file"; fi
done
"""


def benchmark(repeats: int = 3) -> dict[str, Any]:
    if not 1 <= repeats <= 5:
        raise ValueError("每个固定规模仅允许 1–5 次重复。")
    client = Client()
    model_count = client.request("/api/v1/jobs/?kind=explanation")["count"]
    results = []
    for count in (9, 100, 500):
        archive, scale = workload(count)
        imported, analyzed = [], []
        project = client.request("/api/v1/projects/", {"name": f"合成规模评估 {count}"})
        for _ in range(repeats):
            boundary = "v1-" + uuid.uuid4().hex
            body = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="archive"; filename="synthetic.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode()
                + archive
                + f"\r\n--{boundary}--\r\n".encode()
            )
            started = time.monotonic()
            snapshot = client.wait(
                client.request(
                    f"/api/v1/projects/{project['id']}/imports/",
                    body,
                    media="multipart/form-data; boundary=" + boundary,
                )
            )
            imported.append(time.monotonic() - started)
            if snapshot["summary"]["accepted"] != count:
                raise RuntimeError("导入文件数与声明规模不一致。")
            started = time.monotonic()
            analysis = client.wait(
                client.request(
                    f"/api/v1/snapshots/{snapshot['id']}/analyses/",
                    {"root_urlconf": "backend/config/urls.py"},
                )
            )
            analyzed.append(time.monotonic() - started)
            graph = client.request(f"/api/v1/analyses/{analysis['id']}/graph/")
            if not any(
                node["kind"] == "endpoint"
                and node["endpoint"]["method"] == "POST"
                and node["endpoint"]["path"] == "/api/v1/tasks/"
                for node in graph["nodes"]
            ):
                raise RuntimeError("标准创建任务接口未出现在评估结果中。")
        results.append(
            {
                "scale": scale,
                "import": timing_summary(imported),
                "analysis": timing_summary(analyzed),
                "coverage": analysis["coverage"],
                "graph": {
                    key: graph[key]
                    for key in (
                        "total_nodes",
                        "total_edges",
                        "returned_nodes",
                        "returned_edges",
                        "truncated",
                        "truncation_reasons",
                    )
                },
            }
        )
        print(f"真实导入/分析评估：{count} 文件 × {repeats} 次完成。", flush=True)
    if client.request("/api/v1/jobs/?kind=explanation")["count"] != model_count:
        raise RuntimeError("评估期间模型任务数发生变化，不能确认零模型调用。")
    return {
        "workloads": results,
        "timing_scope": "完整 HTTP 提交、排队、执行、结果读取，含 0.2 秒轮询误差",
        "model": {"enabled": False, "calls": 0, "usage": None, "cost": None},
        "limitations": "少量暖缓存单用户串行样本，不报告 p95、SLA 或最大容量",
    }
