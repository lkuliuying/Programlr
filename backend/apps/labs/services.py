"""保留旧实验调用入口，拒绝创建或执行已退役的实验。"""

import uuid
from typing import Any

from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.labs.models import LabRun
from common.retirement import retired_feature


def submit_run(
    key: uuid.UUID, values: dict[str, Any], *, previous: Job | None = None
) -> tuple[Job, bool, bool]:
    retired_feature("lab")


def retry_run(previous: Job, key: uuid.UUID) -> tuple[Job, bool, bool]:
    retired_feature("lab")


def checkpoint(run: LabRun, claim: uuid.UUID) -> None:
    retired_feature("lab")


def execute_run(job_id: str) -> None:
    jobs.refuse_retired_job(job_id)
