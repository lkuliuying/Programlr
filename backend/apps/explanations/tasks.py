from apps.explanations.services import execute_explanation
from config.celery import app

app.task(name="explanations.generate", soft_time_limit=0, time_limit=0)(
    execute_explanation
)
