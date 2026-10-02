from config.settings.local import *  # noqa: F403
from config.settings.local import INSTALLED_APPS

INSTALLED_APPS = [*INSTALLED_APPS, "apps.labs"]
ROOT_URLCONF = "config.lab_urls"
