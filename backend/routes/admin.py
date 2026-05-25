from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models.models import db, User, AuditLog, Role
from functools import wraps
import logging

admin_bp = Blueprint("admin", __name__)
logger = logging.getLogger(__name__)


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
            "role": u.role,
            "is_active": u.is_active,
            "failed_attempts": u.failed_attempts,
            "locked_until": u.locked_until.isoformat() if u.locked_until else None,
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


@admin_bp.route("/logs", methods=["GET"])
@login_required
@admin_required
def get_logs():
    limit = request.args.get("limit", 100, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return jsonify([
        {
            "timestamp": log.timestamp.isoformat(),
            "username": log.username,
            "event_type": log.event_type,
            "description": log.description,
            "ip_address": log.ip_address,
            "success": log.success,
        }
        for log in logs
    ]), 200
