"""
RC Bandito - Authentication Routes
Login, logout, account lockout, and registration
"""

import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models.models import db, User, AuditLog, Role
import logging

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


def log_event(event_type, description, user=None, success=True):
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "anonymous",
        event_type=event_type,
        description=description,
        ip_address=request.remote_addr,
        success=success,
    )
    db.session.add(entry)
    db.session.commit()
    logger.info(f"[{event_type}] {description} | Success: {success}")


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
        log_event("LOGIN_BLOCKED", f"Locked account attempt for '{username}'",
                  user=user, success=False)
        return jsonify({"error": "Account locked. Try again later."}), 403

    if not user.check_password(password):
        user.failed_attempts += 1
        max_attempts = current_app.config["MAX_LOGIN_ATTEMPTS"]

        if user.failed_attempts >= max_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            db.session.commit()
            log_event("ACCOUNT_LOCKED",
                      f"Account '{username}' locked after {max_attempts} failed attempts",
                      user=user, success=False)
            return jsonify({"error": "Account locked for 15 minutes."}), 403

        db.session.commit()
        log_event("LOGIN_FAIL",
                  f"Wrong password for '{username}' (attempt {user.failed_attempts})",
                  user=user, success=False)
        return jsonify({"error": "Invalid credentials."}), 401

    # Successful login
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.session.commit()

    login_user(user)
    log_event("LOGIN_SUCCESS", f"User '{username}' logged in", user=user)

    return jsonify({"message": "Login successful.", "role": user.role}), 200


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    data = request.get_json() or request.form
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # --- Validation ---
    if not username or not email or not password:
        return jsonify({"error": "All fields are required."}), 400

    if len(username) < 3 or len(username) > 80:
        return jsonify({"error": "Username must be 3-80 characters."}), 400

    if not re.match(r"^[A-Za-z0-9_]+$", username):
        return jsonify({"error": "Username can only contain letters, numbers, and underscores."}), 400

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "Invalid email address."}), 400

    # Password policy: 8+ chars, number, upper & lowercase
    if (len(password) < 8
            or not re.search(r"\d", password)
            or not re.search(r"[a-z]", password)
            or not re.search(r"[A-Z]", password)):
        return jsonify({"error": "Password must be 8+ characters with a number, "
                                 "an uppercase and a lowercase letter."}), 400

    # --- Uniqueness checks ---
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken."}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409

    # --- Create user (operator role by default; admins promote via dashboard) ---
    user = User(username=username, email=email, role=Role.OPERATOR)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    log_event("REGISTER", f"New account created: '{username}'", user=user)

    return jsonify({"message": "Account created successfully."}), 201


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_event("LOGOUT", f"User '{current_user.username}' logged out", user=current_user)
    logout_user()
    return jsonify({"message": "Logged out."}), 200
