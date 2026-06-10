"""
RC Bandito - Main Flask Application Entry Point
"""

from flask import Flask, redirect, url_for
from extensions import db, login_manager, limiter
import logging
import os


def create_app():
    app = Flask(__name__, template_folder="../frontend/templates",
                static_folder="../frontend/static")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

    # SQLite - zero setup, creates rc_bandito.db automatically
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

    # Import models so the user_loader gets registered
    from models import models  # noqa: F401

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

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
