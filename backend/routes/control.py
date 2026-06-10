"""
RC Bandito - Control Routes
Command validation, rate limiting, and RC car movement dispatch
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.models import db, AuditLog
from extensions import limiter
import logging
import time

control_bp = Blueprint("control", __name__)
logger = logging.getLogger(__name__)

VALID_COMMANDS = {"forward", "backward", "left", "right", "stop"}
last_command_time = {}
WATCHDOG_TIMEOUT = 3.0


def log_command(description, user, success=True):
    entry = AuditLog(
        user_id=user.id,
        username=user.username,
        event_type="COMMAND",
        description=description,
        ip_address=request.remote_addr,
        success=success,
    )
    db.session.add(entry)
    db.session.commit()


@control_bp.route("/command", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def send_command():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided."}), 400

    command = data.get("command", "").strip().lower()
    speed = data.get("speed", 50)

    if command not in VALID_COMMANDS:
        log_command(f"Rejected invalid command '{command}'", current_user, success=False)
        return jsonify({"error": f"Invalid command. Allowed: {list(VALID_COMMANDS)}"}), 400

    try:
        speed = int(speed)
        if not (0 <= speed <= 100):
            raise ValueError
    except (ValueError, TypeError):
        log_command(f"Rejected out-of-range speed '{speed}'", current_user, success=False)
        return jsonify({"error": "Speed must be an integer between 0 and 100."}), 400

    last_command_time[current_user.id] = time.time()
    dispatch_to_car(command, speed)
    log_command(f"Command '{command}' speed={speed} dispatched", current_user)
    return jsonify({"status": "ok", "command": command, "speed": speed}), 200


@control_bp.route("/emergency_stop", methods=["POST"])
@login_required
def emergency_stop():
    dispatch_to_car("stop", 0)
    log_command("EMERGENCY STOP triggered", current_user)
    return jsonify({"status": "stopped"}), 200


@control_bp.route("/watchdog", methods=["GET"])
@login_required
def watchdog_status():
    last = last_command_time.get(current_user.id, 0)
    elapsed = time.time() - last
    timed_out = elapsed > WATCHDOG_TIMEOUT

    if timed_out and last > 0:
        dispatch_to_car("stop", 0)

    return jsonify({"timed_out": timed_out, "elapsed_seconds": round(elapsed, 2)}), 200


def dispatch_to_car(command: str, speed: int):
    """
    Placeholder: send the command to the RC car.
    Replace with actual GPIO or socket call to the Raspberry Pi.
    """
    logger.info(f"[DISPATCH] command={command} speed={speed}")
