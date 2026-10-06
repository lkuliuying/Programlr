import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.db import (
    DatabaseError,
    IntegrityError,
    close_old_connections,
    connection,
    transaction,
)
from django.db.migrations.executor import MigrationExecutor

from apps.jobs.models import MAX_DISPLAY_ID, OperationLog
from apps.jobs.tests.test_jobs import client_with_token

pytestmark = pytest.mark.django_db(transaction=True)
BASE = datetime(2026, 10, 3, 10, 0, tzinfo=UTC)
SEQUENCE = "jobs_operationlog_display_id_seq"
OLD = [("jobs", "0006_historical_operation_summaries")]
NEW = [("jobs", "0007_operationlog_display_id")]


@pytest.mark.parametrize("count", [0, 3])
def test_number_migration_preserves_old_columns_and_continues_sequence(
    count: int,
) -> None:
    executor = MigrationExecutor(connection)
    restore = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate(OLD)
        old_log = executor.loader.project_state(OLD).apps.get_model(
            "jobs", "OperationLog"
        )
        for index in range(count):
            record = old_log.objects.create(
                id=uuid.UUID(int=index + 1),
                operation="analysis",
                result="succeeded",
                project_name="保留项目",
                object_name=f"旧对象 {index}",
                events=[{"result": "succeeded", "at": BASE.isoformat()}],
            )
            old_log.objects.filter(pk=record.pk).update(
                created_at=BASE + timedelta(days=1 if index == 0 else 0),
                updated_at=BASE + timedelta(minutes=index),
            )
        original: list[dict[str, Any]] = list(old_log.objects.order_by("id").values())
        expected_order = list(
            old_log.objects.order_by("created_at", "id").values_list("id", flat=True)
        )
        MigrationExecutor(connection).migrate(NEW)
        assert dict(OperationLog.objects.values_list("id", "display_id")) == {
            identifier: index + 1 for index, identifier in enumerate(expected_order)
        }
        for row in original:
            current: dict[str, Any] = dict(
                OperationLog.objects.values().get(pk=row["id"])
            )
            assert {field: current[field] for field in row} == row
        # 旧模型没有新列，模拟升级期间仍在运行的旧 Worker。
        legacy_insert = old_log.objects.create(operation="import", result="accepted")
        assert OperationLog.objects.get(pk=legacy_insert.pk).display_id == count + 1
        modern_insert = OperationLog.objects.create(
            operation="source_scan", result="accepted"
        )
        assert modern_insert.display_id == count + 2
        assert isinstance(modern_insert.display_id, int)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_get_serial_sequence('jobs_operationlog', 'display_id')"
            )
            assert cursor.fetchone()[0].endswith(SEQUENCE)
    finally:
        MigrationExecutor(connection).migrate(restore)


def test_direct_legacy_sql_insert_receives_database_generated_number() -> None:
    identifier = uuid.uuid4()
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO jobs_operationlog "
            "(id, operation, result, request_id, project_name, object_name, "
            "source_kind, error_code, events, created_at, updated_at) "
            "VALUES (%s, 'import', 'accepted', '', '旧Worker', '', '', '', "
            "'[]'::jsonb, %s, %s) RETURNING display_id",
            [identifier, BASE, BASE],
        )
        generated = cursor.fetchone()[0]
    log = OperationLog.objects.get(pk=identifier)
    assert 1 <= generated <= MAX_DISPLAY_ID
    assert log.display_id == generated
    assert log.created_at == log.updated_at == BASE


def test_migration_failure_rolls_back_number_column_and_can_retry() -> None:
    executor = MigrationExecutor(connection)
    restore = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate(OLD)
        old_log = executor.loader.project_state(OLD).apps.get_model(
            "jobs", "OperationLog"
        )
        old_log.objects.create(operation="analysis", object_name="失败迁移保留对象")
        original: list[dict[str, Any]] = list(old_log.objects.values())

        def refuse_sequence_publish(
            execute: Callable[..., Any],
            sql: str,
            params: Any,
            many: bool,
            context: dict[str, Any],
        ) -> Any:
            if sql.startswith("SELECT setval('jobs_operationlog_display_id_seq'"):
                raise RuntimeError("本轮夹具模拟回填后失败")
            return execute(sql, params, many, context)

        with (
            connection.execute_wrapper(refuse_sequence_publish),
            pytest.raises(RuntimeError, match="本轮夹具模拟回填后失败"),
        ):
            MigrationExecutor(connection).migrate(NEW)
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(
                cursor, "jobs_operationlog"
            )
            assert "display_id" not in {field.name for field in description}
            cursor.execute("SELECT to_regclass(%s)", [SEQUENCE])
            assert cursor.fetchone()[0] is None
        assert list(old_log.objects.values()) == original
        MigrationExecutor(connection).migrate(NEW)
        migrated = OperationLog.objects.get(pk=original[0]["id"])
        assert migrated.display_id == 1
        current: dict[str, Any] = dict(
            OperationLog.objects.values().get(pk=migrated.pk)
        )
        assert {field: current[field] for field in original[0]} == original[0]
    finally:
        MigrationExecutor(connection).migrate(restore)


def test_concurrent_log_creation_has_globally_unique_database_numbers() -> None:
    def create(index: int) -> tuple[uuid.UUID, int]:
        close_old_connections()
        try:
            row = OperationLog.objects.create(
                operation="analysis",
                object_name=f"并发 {index}",
                project_id=uuid.uuid4(),
            )
            return row.pk, row.display_id
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(create, range(20)))
    assert len({identifier for identifier, _ in records}) == 20
    assert len({number for _, number in records}) == 20
    assert all(isinstance(number, int) and number > 0 for _, number in records)
    assert OperationLog.objects.count() == 20


def test_rolled_back_number_is_not_reused() -> None:
    before = OperationLog.objects.create(operation="analysis")
    abandoned = None
    with pytest.raises(RuntimeError, match="本轮夹具回滚"), transaction.atomic():
        abandoned = OperationLog.objects.create(operation="analysis")
        raise RuntimeError("本轮夹具回滚")
    assert abandoned is not None
    following = OperationLog.objects.create(operation="analysis")
    assert before.display_id < abandoned.display_id < following.display_id
    assert not OperationLog.objects.filter(pk=abandoned.pk).exists()


def test_unique_and_safe_integer_range_are_database_constraints() -> None:
    existing = OperationLog.objects.create(operation="analysis")
    for invalid in [existing.display_id, 0, -1, MAX_DISPLAY_ID + 1]:
        with pytest.raises(IntegrityError), transaction.atomic():
            OperationLog.objects.create(operation="analysis", display_id=invalid)
    assert OperationLog.objects.count() == 1


def test_sequence_stops_at_javascript_safe_integer_without_cycling() -> None:
    OperationLog.objects.create(operation="analysis")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT last_value, is_called FROM {SEQUENCE}")
        previous = cursor.fetchone()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT setval(%s::regclass, %s, false)", [SEQUENCE, MAX_DISPLAY_ID]
            )
        last = OperationLog.objects.create(operation="analysis")
        assert last.display_id == MAX_DISPLAY_ID
        with pytest.raises(DatabaseError), transaction.atomic():
            OperationLog.objects.create(operation="analysis")
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT setval(%s::regclass, %s, %s)", [SEQUENCE, *previous])


def test_bulk_create_and_uuid_detail_preserve_assigned_identity() -> None:
    records = OperationLog.objects.bulk_create(
        [OperationLog(operation="analysis"), OperationLog(operation="import")]
    )
    assert len({row.display_id for row in records}) == 2
    assert all(isinstance(row.display_id, int) for row in records)
    original = {row.pk: row.display_id for row in records}
    records[0].object_name = "修改展示名称"
    records[0].save()
    assert dict(OperationLog.objects.values_list("id", "display_id")) == original
    detail = client_with_token().get(f"/api/v1/operation-logs/{records[0].pk}/")
    assert detail.status_code == 200
    assert detail.json()["id"] == str(records[0].pk)
    assert detail.json()["display_id"] == original[records[0].pk]
