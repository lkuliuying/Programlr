"""自评历史保留读取，新增业务入口统一拒绝。"""

import uuid
from typing import Any

from apps.learning.models import AttemptReview
from common.retirement import retired_feature


def submit_review(key: uuid.UUID, values: dict[str, Any]) -> tuple[AttemptReview, bool]:
    retired_feature("review")
