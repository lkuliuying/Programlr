from apps.projects.services import execute_import
from config.celery import app

app.task(name="projects.import")(execute_import)
