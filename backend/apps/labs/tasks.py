from apps.labs.services import execute_run
from apps.labs.system_services import execute_system_run
from config.celery import app


@app.task(name="labs.run")  # type: ignore[untyped-decorator]
def run_lab(job_id: str) -> None:
    execute_run(job_id)


@app.task(name="labs.system_run")  # type: ignore[untyped-decorator]  # Celery 动态装饰器缺少类型声明。
def run_system_lab(job_id: str) -> None:
    execute_system_run(job_id)
