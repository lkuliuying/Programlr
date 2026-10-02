INSTALLED_APPS = ["rest_framework", "drf_spectacular", "apps.tasks"]
MIDDLEWARE = [
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
APP_ORIGIN = "http://127.0.0.1:5174"
APP_AUTHORITY = "127.0.0.1:5174"
ALLOWED_HOSTS = ["127.0.0.1"]
# Cookie 按主机而非端口隔离，因此示例使用独立名称。
CSRF_COOKIE_NAME = "task_board_csrftoken"
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = False
CSRF_FAILURE_VIEW = "common.middleware.csrf_failure"
DATA_UPLOAD_MAX_MEMORY_SIZE = 4096
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
    "TITLE": "独立任务管理教学示例 API",
    "VERSION": "1.0.0",
    "DESCRIPTION": "从本服务 Serializer/View 自动生成，请勿手工修改；仅包含已实现操作。",
    "COMPONENT_SPLIT_REQUEST": True,
    "SERVE_INCLUDE_SCHEMA": False,
}
