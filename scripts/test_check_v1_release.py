"""验证独立验收资源归属、失败清理、保留测试数据和状态边界。"""

import json
import socket
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_v1_release as release

PROJECT = "learning-lab-v1-verify-012345abcdef"


def state(status: str = "ready") -> dict[str, Any]:
    return {
        "version": 1,
        "project": PROJECT,
        "status": status,
        "origin": release.ORIGIN,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"version": 2},
        {"project": "learning-lab"},
        {"project": "../../existing"},
        {"status": "unknown"},
        {"origin": "https://example.invalid"},
    ],
)
def test_invalid_state_prevents_docker_operation(change: dict[str, Any]) -> None:
    with pytest.raises(RuntimeError):
        release.validate_state({**state(), **change})


def test_inspected_label_mismatch_blocks_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    docker = release.Docker("docker")

    def call(*args: str, timeout: int = 90) -> str:
        calls.append(args)
        return (
            "container-id"
            if args[0] == "ps"
            else json.dumps({"com.docker.compose.project": "existing-project"})
        )

    monkeypatch.setattr(docker, "call", call)
    with pytest.raises(RuntimeError, match="资源归属"):
        release.stop(docker, state(), remove_data=True)
    assert not any("down" in args for args in calls)


@pytest.mark.parametrize("remove_data", [False, True])
def test_cleanup_is_explicit_and_verifies_remaining_resources(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, remove_data: bool
) -> None:
    docker = release.Docker("docker")
    monkeypatch.setattr(release, "STATE", tmp_path / "state.json")
    calls: list[tuple[str, ...]] = []
    retained = [] if remove_data else ["test-volume"]
    monkeypatch.setattr(
        docker,
        "resources",
        lambda project: {"container": [], "network": [], "volume": retained},
    )
    monkeypatch.setattr(docker, "compose", lambda *args, **kwargs: calls.append(args))
    current = state()
    release.stop(docker, current, remove_data=remove_data)
    assert ("--volumes" in calls[0]) == remove_data
    assert current["test_data_retained"] == (not remove_data)
    assert json.loads(release.STATE.read_text())["status"] == "stopped"


def test_cleanup_failure_does_not_mark_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    docker = release.Docker("docker")
    monkeypatch.setattr(
        docker,
        "resources",
        lambda project: {"container": ["left"], "network": [], "volume": []},
    )
    monkeypatch.setattr(docker, "compose", lambda *args, **kwargs: "")
    current = state()
    with pytest.raises(RuntimeError, match="清理未确认"):
        release.stop(docker, current)
    assert current["status"] == "ready"


def test_active_state_never_reuses_existing_stack(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release, "STATE", tmp_path / "state.json")
    release.save_json(release.STATE, state())
    with pytest.raises(RuntimeError, match="已有验收状态"):
        release.start(release.Docker("docker"))


def test_port_conflict_prevents_resource_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release, "STATE", tmp_path / "state.json")
    probe = MagicMock()
    probe.__enter__.return_value.bind.side_effect = OSError("合成端口占用")
    monkeypatch.setattr(socket, "socket", lambda: probe)
    docker = release.Docker("docker")
    resources = MagicMock()
    monkeypatch.setattr(docker, "resources", resources)
    with pytest.raises(RuntimeError, match="5181 端口不可用"):
        release.start(docker)
    resources.assert_not_called()
    assert not release.STATE.exists()


def test_remote_context_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    docker = release.Docker("docker")
    monkeypatch.setattr(docker, "call", lambda *args, **kwargs: "ssh://example.invalid")
    with pytest.raises(RuntimeError, match="远程上下文"):
        docker.local_context()


def test_image_inherited_project_label_cannot_claim_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker = release.Docker("docker")

    def call(*args: str, **kwargs: Any) -> str:
        return (
            "foreign-container"
            if args[0] == "ps"
            else json.dumps({"com.docker.compose.project": PROJECT})
        )

    monkeypatch.setattr(docker, "call", call)
    with pytest.raises(RuntimeError, match="仅继承镜像项目标签"):
        docker.resources(PROJECT)


def test_modified_environment_file_is_never_loaded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release, "DIRECTORY", tmp_path)
    (tmp_path / "empty.env").write_text("UNEXPECTED_CONFIG=synthetic")
    with pytest.raises(RuntimeError, match="环境文件非空"):
        release.Docker("docker").compose(PROJECT, "down")


def test_command_line_restored_after_workflow_failure() -> None:
    previous = sys.argv
    with pytest.raises(RuntimeError), release.arguments(["synthetic-check"]):
        raise RuntimeError("合成检查失败")
    assert sys.argv is previous


def test_start_failure_cleans_own_stack_and_keeps_test_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release, "DIRECTORY", tmp_path)
    monkeypatch.setattr(release, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(socket, "socket", MagicMock())
    docker = release.Docker("docker")
    resources = iter(
        [
            {"container": [], "network": [], "volume": []},
            {"container": [], "network": [], "volume": ["own-volume"]},
            {"container": [], "network": [], "volume": ["own-volume"]},
        ]
    )
    monkeypatch.setattr(docker, "resources", lambda project: next(resources))
    commands: list[tuple[str, ...]] = []

    def compose(*args: str, **kwargs: Any) -> str:
        commands.append(args)
        if "up" in args:
            raise RuntimeError("合成启动失败")
        return ""

    monkeypatch.setattr(docker, "compose", compose)
    with pytest.raises(RuntimeError, match="启动未完成"):
        release.start(docker)
    assert any("down" in args for args in commands)
    assert not any("--volumes" in args for args in commands)
    saved = json.loads(release.STATE.read_text())
    assert saved["status"] == "stopped" and saved["test_data_retained"]


def test_failed_workflow_replaces_previous_success_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release, "REPORT", tmp_path / "report.json")
    release.save_json(release.REPORT, {"status": "passed"})
    docker = release.Docker("docker")
    monkeypatch.setattr(docker, "resources", lambda project: {})
    monkeypatch.setattr(docker, "service", lambda project, service: "own-container")
    monkeypatch.setattr(docker, "call", lambda *args, **kwargs: "synthetic-environment")

    def broken(report: dict[str, Any]) -> None:
        report["current_step"] = "synthetic-failed-step"
        raise AssertionError("合成主线失败")

    monkeypatch.setattr(release, "checks", broken)
    with pytest.raises(RuntimeError, match="验收未通过"):
        release.check(docker, state(), repeats=1)
    saved = json.loads(release.REPORT.read_text())
    assert saved["status"] == "failed"
    assert saved["current_step"] == "synthetic-failed-step"
    assert saved["failure"]["type"] == "AssertionError"
    assert saved["failure"]["location"].startswith("test_check_v1_release.py:")
    assert "合成主线失败" not in release.REPORT.read_text()
