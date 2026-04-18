import cv2 as cv

def open_camera(index=0, backend=cv.CAP_DSHOW):
    cam = cv.VideoCapture(index, backend)
    if not cam.isOpened():
        raise RuntimeError("Could not open camera")
    return cam

def set_camera(cam, width=640, height=480, buffer_size=1):
    cam.set(cv.CAP_PROP_FRAME_WIDTH, width)
    cam.set(cv.CAP_PROP_FRAME_HEIGHT, height)
    cam.set(cv.CAP_PROP_BUFFERSIZE, buffer_size)

def warmup_camera(cam, frames=10):
    for _ in range(frames):
        cam.read()

def read_frame(cam):
    ret, frame = cam.read()
    if not ret:
        raise RuntimeError("Failed to read frame")
    return frame

def frame_to_gray(frame, normalize=False):
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    if normalize:
        gray = gray.astype("float32") / 255.0
    return gray

def show_live_frame(window_name, frame):
    cv.imshow(window_name, frame)

def get_key(delay=1):
    return cv.waitKey(delay) & 0xFF

def release_camera(cam):
    cam.release()
    cv.destroyAllWindows()


# USO EN EL MAIN

import cv2 as cv
import numpy as np

def open_camera(index=0, backend=cv.CAP_DSHOW):
    cam = cv.VideoCapture(index, backend)
    if not cam.isOpened():
        raise RuntimeError("Could not open camera")
    return cam

def set_camera(cam, width=640, height=480, buffer_size=1):
    cam.set(cv.CAP_PROP_FRAME_WIDTH, width)
    cam.set(cv.CAP_PROP_FRAME_HEIGHT, height)
    cam.set(cv.CAP_PROP_BUFFERSIZE, buffer_size)

def warmup_camera(cam, frames=10):
    for _ in range(frames):
        cam.read()

def read_frame(cam):
    ret, frame = cam.read()
    if not ret:
        raise RuntimeError("Failed to read frame")
    return frame

def frame_to_gray(frame, normalize=False):
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    if normalize:
        gray = gray.astype(np.float32) / 255.0
    return gray

def capture_gray_frame(cam, normalize=True):
    frame = read_frame(cam)
    gray = frame_to_gray(frame, normalize=normalize)
    return gray

def show_live_frame(window_name, frame):
    cv.imshow(window_name, frame)

def get_key(delay=1):
    return cv.waitKey(delay) & 0xFF

def release_camera(cam):
    cam.release()
    cv.destroyAllWindows()