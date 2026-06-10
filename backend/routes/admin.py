"""
RC Bandito - Admin Routes
User management and audit log access (admin only)
"""

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from models.models import db, User, AuditLog, Role
from functools import wraps
import logging

admin_bp = Blueprint("admin", __name__)
logger = logging.getLogger(__name__)


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if not current_user.is_admin():
        # Operators get sent to the control panel instead
        from flask import redirect, url_for
        return redirect(url_for("control.dashboard"))
    return render_template("admin.html")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({"error": "Admin access required."}), 403
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def list_users():
    users = User.query.all()
    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "failed_attempts": u.failed_attempts,
            "locked_until": u.locked_until.isoformat() if u.locked_until else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in users
    ]), 200


@admin_bp.route("/users/<int:user_id>/unlock", methods=["POST"])
@login_required
@admin_required
def unlock_user(user_id):
    user = User.query.get_or_404(user_id)
    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()
    return jsonify({"message": f"User '{user.username}' unlocked."}), 200


@admin_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    new_role = data.get("role")

    if new_role not in [Role.ADMIN, Role.OPERATOR]:
        return jsonify({"error": "Invalid role. Use 'admin' or 'operator'."}), 400

    user.role = new_role
    db.session.commit()
    return jsonify({"message": f"Role updated to '{new_role}'."}), 200


@admin_bp.route("/logs", methods=["GET"])
@login_required
@admin_required
def get_logs():
    limit = request.args.get("limit", 100, type=int)
    event_type = request.args.get("type")

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())
    if event_type:
        query = query.filter_by(event_type=event_type.upper())

    logs = query.limit(limit).all()
    return jsonify([
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "username": log.username,
            "event_type": log.event_type,
            "description": log.description,
            "ip_address": log.ip_address,
            "success": log.success,
        }
        for log in logs
    ]), 200
