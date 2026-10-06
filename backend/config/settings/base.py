INSTALLED_APPS = [
    "rest_framework",
    "drf_spectacular",
    "apps.jobs",
    "apps.projects",
    "apps.analysis",
    "apps.explanations",
    "apps.learning",
    "apps.labs",
]
MIDDLEWARE = [
    "apps.jobs.audit_middleware.OperationLogMiddleware",
    "apps.projects.uploads.ImportUploadMiddleware",
    "common.middleware.LocalBoundaryMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "zh-hans"
DEBUG = False
APPEND_SLASH = False
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = False
CSRF_FAILURE_VIEW = "common.middleware.csrf_failure"
DATA_UPLOAD_MAX_MEMORY_SIZE = 4096
DATA_UPLOAD_MAX_NUMBER_FILES = 2001
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5
IMPORT_STORAGE_ROOT = "/var/lib/learning-lab/imports"
IMPORT_LIMITS = {
    "archive_bytes": 20971520,
    "declared_bytes": 104857600,
    "extracted_bytes": 104857600,
    "entries": 5000,
    "source_files": 2000,
    "source_bytes": 1048576,
}
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_SCHEMA_CLASS": "common.schema.ContractSchema",
    "EXCEPTION_HANDLER": "common.errors.api_exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "项目解读实验室基础任务 API",
    "VERSION": "0.1.0",
    "DESCRIPTION": "从本服务 Serializer/View 自动生成，请勿手工修改；仅包含已实现操作。",
    "COMPONENT_SPLIT_REQUEST": True,
    # 扩展图和前端匹配枚举时，保留既有证据与任务状态的生成名称。
    "ENUM_NAME_OVERRIDES": {
        "KindEnum": ["source_fact", "static_inference", "framework_rule"],
        "StatusEnum": "apps.jobs.models.Job.Status",
        "FrontendMatchStatusEnum": ["confirmed", "candidate", "unmatched"],
        "ComparisonFileChangeEnum": "apps.analysis.diffs.types.FILE_CHANGE_TYPES",
        "SemanticChangeEnum": "apps.analysis.diffs.types.SEMANTIC_CHANGE_TYPES",
    },
    "SERVE_INCLUDE_SCHEMA": False,
}
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_PUBLISH_RETRY = False
CELERY_BROKER_CONNECTION_TIMEOUT = 2
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 3
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "socket_connect_timeout": 2,
    "socket_timeout": 2,
    "retry_on_timeout": False,
    "max_retries": 0,
}
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_CONCURRENCY = 1
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_TASK_SOFT_TIME_LIMIT = 0
CELERY_TASK_TIME_LIMIT = 0
CELERY_TASK_ANNOTATIONS = {
    name: {"soft_time_limit": 290, "time_limit": 300}
    for name in (
        "jobs.system_check",
        "projects.import",
        "analysis.parse",
        "analysis.source_scan",
        "jobs.delete",
        "analysis.compare",
        "labs.run",
        "labs.system_run",
    )
}
MODEL_OPTIONS: dict[str, str] = {}
