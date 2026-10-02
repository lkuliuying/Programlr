"""核对固定合成规模与资源测量的边界和未知值语义。"""

import io
import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v1_acceptance as acceptance
from v1_acceptance import read_memory_metrics, timing_summary, workload


@pytest.mark.parametrize("count", [9, 100, 500])
def test_workload_is_deterministic_and_matches_scale(count: int) -> None:
    value, scale = workload(count)
    assert value == workload(count)[0]
    with zipfile.ZipFile(io.BytesIO(value)) as archive:
        assert len(archive.namelist()) == count
        assert (
            sum(len(archive.read(name)) for name in archive.namelist())
            == scale["source_bytes"]
        )
        assert "backend/config/urls.py" in archive.namelist()
        assert not any(
            name.startswith("/") or ".." in name for name in archive.namelist()
        )


@pytest.mark.parametrize("count", [0, 8, 501])
def test_workload_rejects_unbounded_scale(count: int) -> None:
    with pytest.raises(ValueError):
        workload(count)


def test_memory_v2_and_v1_fallback() -> None:
    v2 = read_memory_metrics(
        "v2_peak=1024\nv2_current=512\nv2_limit=max\npids_current=4"
    )
    assert v2["memory_peak_bytes"] == 1024 and v2["memory_limit_bytes"] is None
    assert v2["cgroup_version"] == "v2" and v2["pids_current"] == 4
    v1 = read_memory_metrics("v1_peak=2048\nv1_current=1024\nv1_limit=4096")
    assert v1["memory_peak_bytes"] == 2048 and v1["cgroup_version"] == "v1"
    assert not v1["unavailable"]


def test_unavailable_memory_is_not_zero() -> None:
    result = read_memory_metrics("v2_peak=unavailable\nv1_peak=-1")
    assert result["unavailable"] and result["memory_peak_bytes"] is None
    assert result["memory_current_bytes"] is None


def test_timing_reports_individual_samples() -> None:
    result = timing_summary([3.0, 1.0, 2.0])
    assert result["median_seconds"] == 2.0 and result["sample_count"] == 3
    assert result["min_seconds"] == 1.0 and result["max_seconds"] == 3.0


@pytest.mark.parametrize("samples", [[], [-1.0], [float("nan")], [float("inf")]])
def test_invalid_timings_rejected(samples: list[float]) -> None:
    with pytest.raises(ValueError):
        timing_summary(samples)


def test_incorrect_published_cards_stops_before_submissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.request.return_value = {"count": 0, "results": []}
    monkeypatch.setattr(acceptance, "Client", lambda: client)
    with pytest.raises(RuntimeError, match="知识卡片"):
        acceptance.learning_checks({})
    client.request.assert_called_once_with("/api/v1/knowledge-cards/?page_size=100")


def test_leaked_exercise_answer_stops_before_submissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cards = [
        item
        for source in (acceptance.ROOT / "content/knowledge").glob("*.json")
        for item in json.loads(source.read_text(encoding="utf-8"))
    ]
    bundle = json.loads(
        (acceptance.ROOT / "content/exercises/task-board-create.json").read_text(
            encoding="utf-8"
        )
    )
    exercises = [
        {"slug": item["slug"], "applicable": True, "answer": "合成泄漏值"}
        for item in bundle["exercises"]
    ]
    client = MagicMock()
    client.request.side_effect = [
        {"count": len(cards), "results": cards},
        {"results": exercises},
    ]
    monkeypatch.setattr(acceptance, "Client", lambda: client)
    with pytest.raises(RuntimeError, match="答案保密"):
        acceptance.learning_checks(
            {
                "analysis_id": "synthetic",
                "endpoint_index": 6,
                "snapshot_id": "synthetic",
            }
        )
    assert client.request.call_count == 2
    assert all(len(call.args) == 1 for call in client.request.call_args_list)
