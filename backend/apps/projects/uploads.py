import re
import uuid
from collections.abc import Callable

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.http import HttpRequest, HttpResponse, JsonResponse

from common.errors import error_body


class BoundedUploadHandler(TemporaryFileUploadHandler):
    def receive_data_chunk(self, raw_data: bytes, start: int) -> None:
        if start + len(raw_data) > settings.IMPORT_LIMITS["archive_bytes"]:
            self.file.close()
            raise RequestDataTooBig
        super().receive_data_chunk(raw_data, start)


def configure_upload(request: HttpRequest) -> bool:
    is_import = bool(
        re.fullmatch(r"/api/v1/projects/[0-9a-fA-F-]{36}/imports/", request.path)
        or (
            re.fullmatch(r"/api/v1/jobs/[0-9a-fA-F-]{36}/retries/", request.path)
            and request.content_type == "multipart/form-data"
        )
    )
    if not is_import or request.method != "POST":
        return False
    setattr(request, "import_upload", True)
    raw = request.META.get("CONTENT_LENGTH", "")
    if not raw.isascii() or not raw.isdecimal() or len(raw) > 12:
        raise RequestDataTooBig
    if int(raw) > settings.IMPORT_LIMITS["archive_bytes"] + 65536:
        raise RequestDataTooBig
    request.upload_handlers = [BoundedUploadHandler(request)]
    return True


class ImportUploadMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            configure_upload(request)
        except RequestDataTooBig:
            request_id = uuid.uuid4().hex
            response = JsonResponse(
                error_body(
                    "ARCHIVE_LIMIT_EXCEEDED",
                    "上传超过接收限制或缺少有效长度。",
                    request_id,
                ),
                status=413,
            )
            response["X-Request-ID"] = request_id
            response["Cache-Control"] = "no-store"
            return response
        return self.get_response(request)
