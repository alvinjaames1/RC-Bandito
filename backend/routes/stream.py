"""
RC Bandito - Video Stream Routes
Live MJPEG stream from the car's camera.

Camera priority:
1. Raspberry Pi ribbon camera via picamera2 (the Freenove kit camera)
2. Fallback: any USB webcam via OpenCV (index 0)
If neither is available, /stream/status reports camera_active: false.
"""

from flask import Blueprint, Response, jsonify
from flask_login import login_required
import logging
import cv2

stream_bp = Blueprint("stream", __name__)
logger = logging.getLogger(__name__)

_picam = None
_cvcam = None
_mode = None  # "picamera2", "opencv", or None


def init_camera():
    global _picam, _cvcam, _mode
    if _mode is not None:
        return _mode

    # Try the Pi ribbon camera first (Freenove kit camera)
    try:
        from picamera2 import Picamera2
        _picam = Picamera2()
        config = _picam.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        _picam.configure(config)
        _picam.start()
        _mode = "picamera2"
        logger.info("[STREAM] Using Raspberry Pi camera (picamera2).")
        return _mode
    except Exception as e:
        logger.warning(f"[STREAM] picamera2 not available ({e}). Trying USB webcam...")

    # Fallback: USB webcam
    try:
        _cvcam = cv2.VideoCapture(0)
        if _cvcam.isOpened():
            _mode = "opencv"
            logger.info("[STREAM] Using USB webcam (OpenCV index 0).")
            return _mode
        _cvcam = None
    except Exception as e:
        logger.warning(f"[STREAM] OpenCV webcam failed: {e}")

    logger.error("[STREAM] No camera available.")
    _mode = None
    return _mode


def generate_frames():
    mode = init_camera()

    while mode == "picamera2":
        frame = _picam.capture_array()               # RGB888 numpy array
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

    while mode == "opencv":
        success, frame = _cvcam.read()
        if not success:
            break
        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")


@stream_bp.route("/video_feed")
@login_required
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@stream_bp.route("/status")
@login_required
def stream_status():
    mode = init_camera()
    return jsonify({"camera_active": mode is not None, "mode": mode}), 200
