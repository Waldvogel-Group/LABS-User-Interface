import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.exceptions import HTTPException
from flask_migrate import Migrate

# instantiate extensions
login_manager = LoginManager()
db = SQLAlchemy()
migrate = Migrate()


def create_app(environment="development"):
    from config import config
    from .views import main_blueprint
    from .auth.views import auth_blueprint
    from .auth.models import User, AnonymousUser

    # from .experiments.models import ExperimentalDesign, ExperimentalStation
    from .monitoring.views import monitoring_blueprint
    from .experiments.views import experiments_blueprint

    # Instantiate app.
    app = Flask(__name__)

    # Set app config.
    env = os.environ.get("FLASK_ENV", environment)
    app.config.from_object(config[env])
    config[env].configure(app)

    # Set up extensions.

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    # user_manager = UserManager(app, db, User)

    # Register blueprints.
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(monitoring_blueprint)
    app.register_blueprint(experiments_blueprint)

    # user_manager = UserManager(app, db, User)

    # Set up flask login.
    @login_manager.user_loader
    def get_user(id):
        return User.query.get(int(id))

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.anonymous_user = AnonymousUser

    with app.app_context():
        # create database tables
        # create default admin
        User.add_admin_user()

    # Error handlers.
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return render_template("error.html", error=error), error.code

    return app
