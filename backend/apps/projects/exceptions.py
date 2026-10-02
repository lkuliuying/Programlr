class ImportRejected(Exception):
    def __init__(
        self, reason: str, *, limit: bool = False, storage: bool = False
    ) -> None:
        self.reason = reason
        self.code = (
            "IMPORT_STORAGE_FAILED"
            if storage
            else "ARCHIVE_LIMIT_EXCEEDED"
            if limit
            else "INVALID_ARCHIVE"
        )
        self.message = (
            "导入存储暂不可用。"
            if storage
            else "归档超过资源限制，请缩小导入范围。"
            if limit
            else "归档不符合安全或源码范围要求。"
        )
        super().__init__(self.code)
