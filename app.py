"""
RC Bandito - Main Flask Application Entry Point
"""

from flask import Flask
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
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://root:password@localhost/rc_bandito"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_LOGIN_ATTEMPTS"] = 5

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access the control panel."

    logging.basicConfig(
        filename="logs/rc_bandito.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    from routes.auth import auth_bp
    from routes.control import control_bp
    from routes.admin import admin_bp
    from routes.stream import stream_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(control_bp, url_prefix="/control")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(stream_bp, url_prefix="/stream")

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    app = create_app()
    # Use ssl_context for TLS in production
    app.run(host="0.0.0.0", port=5000, debug=True)
