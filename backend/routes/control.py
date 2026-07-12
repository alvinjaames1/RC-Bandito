"""
RC Bandito - Control Routes
Command validation, rate limiting, and RC car movement dispatch.

Motor integration: Freenove 4WD Smart Car kit v2.0
(class Ordinary_Car, method set_motor_model, PCA9685 over I2C).
Falls back to log-only mode on machines without the hardware,
so the app still runs on laptops for development.
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models.models import db, AuditLog
from extensions import limiter
import logging
import time

control_bp = Blueprint("control", __name__)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
# Freenove v2.0 motor hardware (only available on the Raspberry Pi)
# ---------------------------------------------------------------
try:
    from motor import Ordinary_Car       # backend/motor.py (copied from Freenove Code/Server)
    PWM = Ordinary_Car()
    HARDWARE_AVAILABLE = True
    logger.info("[HARDWARE] Freenove Ordinary_Car motor driver initialized.")
except Exception as e:
    PWM = None
    HARDWARE_AVAILABLE = False
    logger.warning(f"[HARDWARE] Motor driver not available ({e}). Running in log-only mode.")


VALID_COMMANDS = {"forward", "backward", "left", "right", "stop"}
last_command_time = {}
WATCHDOG_TIMEOUT = 3.0


@control_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("control.html")


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
    return jsonify({"status": "ok", "command": command, "speed": speed,
                    "hardware": HARDWARE_AVAILABLE}), 200


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
        dispatch_to_car("stop", 0)   # physical failsafe: halt the motors

    return jsonify({"timed_out": timed_out, "elapsed_seconds": round(elapsed, 2)}), 200


# ---------------------------------------------------------------
# Motor dispatch (Freenove v2.0 API)
# ---------------------------------------------------------------
def speed_to_duty(speed: int) -> int:
    """Map UI speed (0-100) to PWM duty (0-4000, inside the 4096 range)."""
    return int(speed * 40)


def dispatch_to_car(command: str, speed: int):
    """
    Drive the Freenove 4WD motors.
    set_motor_model(left_front, left_rear, right_front, right_rear)
    Positive duty = forward, negative = reverse, 0 = stop.
    """
    duty = speed_to_duty(speed)

    motor_map = {
        "forward":  ( duty,  duty,  duty,  duty),
        "backward": (-duty, -duty, -duty, -duty),
        "left":     (-duty, -duty,  duty,  duty),   # left wheels reverse, right forward
        "right":    ( duty,  duty, -duty, -duty),
        "stop":     (0, 0, 0, 0),
    }

    duties = motor_map[command]

    if HARDWARE_AVAILABLE:
        PWM.set_motor_model(*duties)
        logger.info(f"[MOTOR] {command} -> set_motor_model{duties}")
    else:
        logger.info(f"[DISPATCH-SIM] {command} speed={speed} (no hardware) -> {duties}")
