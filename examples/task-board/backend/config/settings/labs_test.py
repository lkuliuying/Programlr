from config.settings.test import *  # noqa: F403
from config.settings.test import INSTALLED_APPS

INSTALLED_APPS = [*INSTALLED_APPS, "apps.labs"]
ROOT_URLCONF = "config.lab_urls"
