import re
import uuid
from collections.abc import Callable

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.http import HttpRequest, HttpResponse, JsonResponse

from apps.projects.folder import FOLDER_BODY_BYTES, FOLDER_BYTES, MANIFEST_BYTES
from common.errors import error_body


class BoundedUploadHandler(TemporaryFileUploadHandler):
    def __init__(self, request: HttpRequest, *, folder: bool = False) -> None:
        super().__init__(request)
        self.folder = folder
        self.received = 0

    def receive_data_chunk(self, raw_data: bytes, start: int) -> None:
        self.received += len(raw_data)
        file_limit = (
            MANIFEST_BYTES
            if self.folder and self.field_name == "manifest"
            else 1024 * 1024
            if self.folder
            else settings.IMPORT_LIMITS["archive_bytes"]
        )
        total_limit = (
            FOLDER_BYTES + MANIFEST_BYTES
            if self.folder
            else settings.IMPORT_LIMITS["archive_bytes"]
        )
        if start + len(raw_data) > file_limit or self.received > total_limit:
            self.file.close()
            raise RequestDataTooBig
        super().receive_data_chunk(raw_data, start)


def configure_upload(request: HttpRequest) -> bool:
    folder = bool(
        re.fullmatch(r"/api/v1/projects/[0-9a-fA-F-]{36}/folder-imports/", request.path)
        or re.fullmatch(r"/api/v1/jobs/[0-9a-fA-F-]{36}/folder-retries/", request.path)
    )
    is_import = bool(
        folder
        or re.fullmatch(r"/api/v1/projects/[0-9a-fA-F-]{36}/imports/", request.path)
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
    if int(raw) > (
        FOLDER_BODY_BYTES if folder else settings.IMPORT_LIMITS["archive_bytes"] + 65536
    ):
        raise RequestDataTooBig
    request.upload_handlers = [BoundedUploadHandler(request, folder=folder)]
    return True


class ImportUploadMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            configure_upload(request)
        except RequestDataTooBig:
            request_id = getattr(request, "request_id", uuid.uuid4().hex)
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
