import os
from flask import Flask
from raven.contrib.flask import Sentry
from plenario.database import session as db_session
from plenario.models import bcrypt
from plenario.api import api
from plenario.auth import auth, login_manager
from plenario.views import views
from urllib import quote_plus

sentry = Sentry(dsn=os.environ['WOPR_SENTRY_URL'])

def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.secret_key = os.environ['FLASK_KEY']
    login_manager.init_app(app)
    bcrypt.init_app(app)
    sentry.init_app(app)
    app.register_blueprint(api)
    app.register_blueprint(views)
    app.register_blueprint(auth)
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()
    return app

