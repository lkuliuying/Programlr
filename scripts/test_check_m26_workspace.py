import json
from copy import deepcopy
from typing import Any

import pytest
from check_m26_workspace import LABEL, ORIGIN, ROLES, Docker, validate_state


def state() -> dict[str, Any]:
    tag = "learning-lab-m26-verify-123456abcdef"
    return {
        "version": 2,
        "tag": tag,
        "origin": ORIGIN,
        "status": "ready",
        "containers": [tag + "-" + role for role in ROLES],
        "network": tag + "-network",
        "entry_network": tag + "-entry",
        "volume": tag + "-imports",
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("origin", "http://127.0.0.1:5181"),
        ("tag", "learning-lab-v1-verify-123456abcdef"),
        ("volume", "import-data"),
        ("entry_network", "foreign-entry"),
        ("containers", ["foreign-api"]),
        ("status", "unknown"),
    ],
)
def test_state_rejects_foreign_names_or_origin(key: str, value: Any) -> None:
    document = state()
    assert validate_state(deepcopy(document)) == document
    document[key] = value
    with pytest.raises(RuntimeError):
        validate_state(document)


def test_local_context_rejects_remote_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    docker = Docker("docker")
    monkeypatch.setattr(
        docker, "call", lambda *args, **kwargs: "tcp://remote.invalid:2376"
    )
    with pytest.raises(RuntimeError):
        docker.local_context()


def test_cleanup_inventory_rejects_foreign_label_on_expected_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = state()
    docker = Docker("docker")

    def response(*args: str, **kwargs: Any) -> str:
        if args[:2] == ("ps", "-aq"):
            return ""
        if args[:2] == ("ps", "-a"):
            return str(document["tag"]) + "-api"
        return ""

    monkeypatch.setattr(docker, "call", response)
    with pytest.raises(RuntimeError):
        docker.owned(document)


def test_cleanup_inventory_rejects_extra_resources_even_with_owner_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = state()
    docker = Docker("docker")

    def response(*args: str, **kwargs: Any) -> str:
        if args[:2] == ("ps", "-aq"):
            return "id"
        if "{{json .Name}}" in args:
            return json.dumps("/" + document["tag"] + "-foreign")
        if "{{json .Config.Labels}}" in args:
            return json.dumps({LABEL: document["tag"], LABEL + ".role": "foreign"})
        return ""

    monkeypatch.setattr(docker, "call", response)
    with pytest.raises(RuntimeError):
        docker.owned(document)


def test_legacy_state_remains_cleanable_without_inventing_entry_network() -> None:
    document = state()
    document["version"] = 1
    del document["entry_network"]
    assert validate_state(document) == document
    document["entry_network"] = str(document["tag"]) + "-entry"
    with pytest.raises(RuntimeError):
        validate_state(document)


def test_both_networks_require_exact_owner_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = state()
    docker = Docker("docker")
    networks = [str(document["network"]), str(document["entry_network"])]

    def response(*args: str, **kwargs: Any) -> str:
        if args[:3] == ("network", "ls", "-q"):
            return "\n".join(networks)
        if args[:2] == ("network", "ls"):
            return "\n".join(networks)
        if args[:2] == ("network", "inspect"):
            name = args[-1]
            if "{{json .Name}}" in args:
                return json.dumps(name)
            return json.dumps(
                {
                    LABEL: document["tag"],
                    LABEL + ".role": name.removeprefix(str(document["tag"]) + "-"),
                }
            )
        return ""

    monkeypatch.setattr(docker, "call", response)
    assert docker.owned(document)["network"] == networks

    def foreign_entry(*args: str, **kwargs: Any) -> str:
        if args[:3] == ("network", "ls", "-q"):
            return str(document["network"])
        return response(*args, **kwargs)

    monkeypatch.setattr(docker, "call", foreign_entry)
    with pytest.raises(RuntimeError):
        docker.owned(document)
