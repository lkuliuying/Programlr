from apps.analysis.diffs.services import execute_comparison
from apps.analysis.services import execute_analysis
from config.celery import app

app.task(name="analysis.parse")(execute_analysis)
app.task(name="analysis.compare")(execute_comparison)
