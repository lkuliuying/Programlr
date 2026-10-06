from apps.analysis.diffs.services import execute_comparison
from apps.analysis.scans import execute_source_scan
from apps.analysis.services import execute_analysis
from config.celery import app

app.task(name="analysis.source_scan")(execute_source_scan)

app.task(name="analysis.parse")(execute_analysis)
app.task(name="analysis.compare")(execute_comparison)
