"""类型插件和无数据库测试所需的隔离配置，不用于运行服务。"""

INSTALLED_APPS: list[str] = []
DATABASES: dict[str, object] = {}
USE_TZ = True
REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None}
