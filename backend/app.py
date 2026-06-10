"""
RC Bandito - Main Flask Application Entry Point
(Updated: uses SQLite so no database setup is needed.
 To switch to MySQL later, change DATABASE_URL back to the mysql+pymysql:// string.)
"""

from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os

db = SQLAlchemy()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)


def create_app():
    app = Flask(__name__, template_folder="../frontend/templates",
                static_folder="../frontend/static")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

    # SQLite - zero setup, creates rc_bandito.db automatically in the backend folder
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///rc_bandito.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_LOGIN_ATTEMPTS"] = 5

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access the control panel."

    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        filename="logs/rc_bandito.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from routes.auth import auth_bp
    from routes.control import control_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(control_bp, url_prefix="/control")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Video stream needs opencv + a camera. Loaded safely so the app
    # still runs on a laptop without a camera attached.
    try:
        from routes.stream import stream_bp
        app.register_blueprint(stream_bp, url_prefix="/stream")
    except ImportError:
        logging.warning("OpenCV not installed - video streaming disabled for now.")

    # Convenience: visiting http://localhost:5000/ goes straight to the login page
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
