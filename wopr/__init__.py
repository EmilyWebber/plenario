import os
from flask import Flask
from celery import Task, Celery
from celery.schedules import crontab
from wopr.database import session as db_session
from wopr.api import api
from wopr.views import views

BROKER_URL = 'sqs://%s:%s@' % (os.environ['AWS_ACCESS_KEY'], os.environ['AWS_SECRET_KEY'])

CELERYBEAT_SCHEDULE = {
    'update_crime_every_day': {
        'task': 'wopr.tasks.update_crime',
        'schedule': crontab(minute=0, hour=8),
    }
}

def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.register_blueprint(api)
    app.register_blueprint(views)
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()
    return app

def make_celery(app=None):
    app = app or create_app()
    celery_app = Celery(app.import_name, broker=BROKER_URL)
    celery_app.conf['CELERY_IMPORTS'] = ('wopr.tasks',)
    celery_app.conf['CELERYBEAT_SCHEDULE'] = CELERYBEAT_SCHEDULE
    celery_app.conf['CELERY_TIMEZONE'] = 'America/Chicago'
    TaskBase = celery_app.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery_app.Task  = ContextTask
    return celery_app
