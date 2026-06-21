from flask import Blueprint, Response, jsonify
from flask_login import login_required
import logging
import cv2

stream_bp = Blueprint("stream", __name__)
logger = logging.getLogger(__name__)
camera = None


def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture("http://192.168.1.65:8080/video")
    return camera


def generate_frames():
    cam = get_camera()
    while True:
        success, frame = cam.read()
        if not success:
            break
        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")


@stream_bp.route("/video_feed")
@login_required
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@stream_bp.route("/status")
@login_required
def stream_status():
    cam = get_camera()
    return jsonify({"camera_active": cam is not None and cam.isOpened()}), 200
