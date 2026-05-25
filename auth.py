"""
RC Bandito - Authentication Routes
Login, logout, and account lockout handling
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models.models import db, User, AuditLog
import logging

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


def log_event(event_type, description, user=None, success=True):
    ip = request.remote_addr
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "anonymous",
        event_type=event_type,
        description=description,
        ip_address=ip,
        success=success,
    )
    db.session.add(entry)
    db.session.commit()
    logger.info(f"[{event_type}] {description} | IP: {ip} | Success: {success}")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    data = request.get_json() or request.form
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    user = User.query.filter_by(username=username).first()

    if not user:
        log_event("LOGIN_FAIL", f"Unknown user '{username}'", success=False)
        return jsonify({"error": "Invalid credentials."}), 401

    if user.is_locked():
        log_event("LOGIN_BLOCKED", f"Locked account access attempt for '{username}'", user=user, success=False)
        return jsonify({"error": "Account locked. Try again later."}), 403

    if not user.check_password(password):
        user.failed_attempts += 1
        max_attempts = current_app.config["MAX_LOGIN_ATTEMPTS"]

        if user.failed_attempts >= max_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            log_event("ACCOUNT_LOCKED", f"Account '{username}' locked after {max_attempts} failed attempts", user=user, success=False)
            db.session.commit()
            return jsonify({"error": "Account locked for 15 minutes after too many failed attempts."}), 403

        db.session.commit()
        log_event("LOGIN_FAIL", f"Wrong password for '{username}' (attempt {user.failed_attempts})", user=user, success=False)
        return jsonify({"error": "Invalid credentials."}), 401

    # Successful login
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.session.commit()

    login_user(user)
    log_event("LOGIN_SUCCESS", f"User '{username}' logged in", user=user)

    return jsonify({"message": "Login successful.", "role": user.role}), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_event("LOGOUT", f"User '{current_user.username}' logged out", user=current_user)
    logout_user()
    return jsonify({"message": "Logged out successfully."}), 200
