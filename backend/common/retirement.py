from typing import NoReturn

from common.errors import ApiProblem

RETIRED_JOB_KINDS = frozenset({"lab", "snapshot_comparison", "system_check"})


def retired_feature(feature: str) -> NoReturn:
    raise ApiProblem(
        410,
        "FEATURE_RETIRED",
        "该功能已退役，仅保留历史记录。",
        {"feature": feature},
    )


def require_active_job_kind(kind: str) -> None:
    if kind in RETIRED_JOB_KINDS:
        retired_feature(kind)
