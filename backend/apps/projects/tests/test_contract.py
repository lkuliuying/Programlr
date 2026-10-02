import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.jobs.tests.test_contract import contract_schema
from config.environment import import_limit


def test_project_request_contract_has_no_extra_fields() -> None:
    schema = contract_schema()
    components = schema["components"]["schemas"]
    for name in ("ProjectInputRequest", "ImportInputRequest"):
        assert components[name]["additionalProperties"] is False
    upload = schema["paths"]["/api/v1/projects/{project_id}/imports/"]["post"]
    assert upload["requestBody"]["required"]
    assert set(upload["requestBody"]["content"]) == {"multipart/form-data"}
    assert (
        components["ImportInputRequest"]["properties"]["archive"]["format"] == "binary"
    )
    assert {"200", "202", "400", "409", "413", "415", "503"} <= upload[
        "responses"
    ].keys()


def test_resource_config_can_only_reduce_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert import_limit("IMPORT_TEST_LIMIT", 20) == 20
    monkeypatch.setenv("IMPORT_TEST_LIMIT", "10")
    assert import_limit("IMPORT_TEST_LIMIT", 20) == 10
    for value in ("0", "-1", "21", "１", "1.5", "invalid"):
        monkeypatch.setenv("IMPORT_TEST_LIMIT", value)
        with pytest.raises(ImproperlyConfigured):
            import_limit("IMPORT_TEST_LIMIT", 20)


def test_snapshot_name_contract_is_strict_metadata_patch() -> None:
    schema = contract_schema()
    components = schema["components"]["schemas"]
    patch = schema["paths"]["/api/v1/snapshots/{snapshot_id}/"]["patch"]
    reference = patch["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    name = components[reference.rsplit("/", 1)[1]]
    assert name["additionalProperties"] is False
    assert set(name["properties"]) == {"name"}
    assert name["required"] == ["name"]
    assert name["properties"]["name"]["maxLength"] == 200
    assert "name" in components["Snapshot"]["properties"]
    assert set(patch["requestBody"]["content"]) == {"application/json"}
    assert {"200", "400", "403", "404", "415"} <= patch["responses"].keys()
    assert {
        parameter["name"]
        for parameter in patch["parameters"]
        if parameter["in"] == "header"
    } == {"Origin", "X-CSRFToken"}
