import os
import sys

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Load the recommender when the development server starts serving, not
        # for every manage.py command. runserver's autoreloader runs the
        # project twice; only the serving process has RUN_MAIN set.
        serving = 'runserver' in sys.argv and (os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv)
        if serving:
            from core.services import warm_up
            warm_up()
