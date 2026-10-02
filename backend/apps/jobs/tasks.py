from apps.jobs.services import execute_check
from config.celery import app

app.task(name="jobs.system_check")(execute_check)
