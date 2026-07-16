"""
RC Bandito - Main Flask Application Entry Point (hardened)

Security features:
- TLS/HTTPS with self-signed certificate (if cert.pem/key.pem exist)
- SECRET_KEY loaded from .env (falls back to a random key per run)
- Secure session cookies (Secure, HttpOnly, SameSite)
- 30-minute session timeout
- Debug mode off by default (enable with FLASK_DEBUG=1 in .env)
"""

from flask import Flask, redirect, url_for
from extensions import db, login_manager, limiter
from datetime import timedelta
import logging
import secrets
import os

# Load .env if python-dotenv is installed (optional but recommended)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def create_app():
    app = Flask(__name__, template_folder="../frontend/templates",
                static_folder="../frontend/static")

    # --- Secret key: from .env, or a random one generated at startup ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///rc_bandito.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_LOGIN_ATTEMPTS"] = 5

    # --- Secure session cookies ---
    app.config["SESSION_COOKIE_SECURE"] = True      # only sent over HTTPS
    app.config["SESSION_COOKIE_HTTPONLY"] = True    # JavaScript cannot read it
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"   # CSRF protection
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

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

    try:
        from routes.stream import stream_bp
        app.register_blueprint(stream_bp, url_prefix="/stream")
    except ImportError:
        logging.warning("Camera libraries not installed - video streaming disabled.")

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()

    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    # --- TLS: use HTTPS if certificate files are present ---
    cert_exists = os.path.exists("cert.pem") and os.path.exists("key.pem")
    if cert_exists:
        print(" * TLS enabled - serving on https://0.0.0.0:5000")
        app.run(host="0.0.0.0", port=5000, debug=debug,
                ssl_context=("cert.pem", "key.pem"))
    else:
        print(" * WARNING: cert.pem/key.pem not found - serving over plain HTTP.")
        print(" * Generate them with:")
        print('   openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=rc-bandito"')
        # Without HTTPS, the Secure cookie flag would block logins - relax it
        app.config["SESSION_COOKIE_SECURE"] = False
        app.run(host="0.0.0.0", port=5000, debug=debug)
