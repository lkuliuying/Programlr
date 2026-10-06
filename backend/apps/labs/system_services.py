"""保留旧系统实验任务名，拒绝提交和执行已退役的实验。"""

import uuid
from typing import Any

from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.labs.models import SystemLabRun
from common.retirement import retired_feature


def submit_system_run(
    lab_id: str, key: uuid.UUID, values: dict[str, Any], *, previous: Job | None = None
) -> tuple[Job, bool, bool]:
    retired_feature("lab")


def retry_system_run(previous: Job, key: uuid.UUID) -> tuple[Job, bool, bool]:
    retired_feature("lab")


def checkpoint(run: SystemLabRun, claim: uuid.UUID) -> None:
    retired_feature("lab")


def execute_system_run(job_id: str) -> None:
    jobs.refuse_retired_job(job_id)
