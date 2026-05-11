import cv2 as cv
import numpy as np


def open_camera(indexes=(0, 1, 2), backends=None):
    """
    Intenta abrir una cámara probando varios índices y backends.

    Windows normalmente usa CAP_DSHOW.
    Raspberry/Linux normalmente usa CAP_V4L2.
    CAP_ANY deja que OpenCV decida automáticamente.
    """

    if isinstance(indexes, int):
        indexes = (indexes,)

    if backends is None:
        backends = [
            ("DSHOW / Windows", cv.CAP_DSHOW),
            ("V4L2 / Raspberry-Linux", cv.CAP_V4L2),
            ("ANY / OpenCV auto", cv.CAP_ANY),
        ]

    attempts = []

    for index in indexes:
        for backend_name, backend in backends:
            cam = cv.VideoCapture(index, backend)

            if cam.isOpened():
                print(f"Camera opened at index {index} with backend: {backend_name}")
                return cam

            cam.release()
            attempts.append(f"index={index}, backend={backend_name}")

    raise RuntimeError(
        "Could not open any camera. Tried:\n" + "\n".join(attempts)
    )


def set_camera(cam, width=640, height=480, fps=None, buffer_size=1):
    """
    Configura parámetros básicos de la cámara.
    No todas las webcams aceptan todos los parámetros.
    """

    cam.set(cv.CAP_PROP_FRAME_WIDTH, width)
    cam.set(cv.CAP_PROP_FRAME_HEIGHT, height)
    cam.set(cv.CAP_PROP_BUFFERSIZE, buffer_size)

    if fps is not None:
        cam.set(cv.CAP_PROP_FPS, fps)


def warmup_camera(cam, frames=10):
    """
    Lee algunos frames iniciales para estabilizar exposición/autoajustes.
    """

    for _ in range(frames):
        cam.read()


def read_frame(cam):
    """
    Lee un frame BGR desde la cámara.
    """

    ret, frame = cam.read()

    if not ret or frame is None:
        raise RuntimeError("Failed to read frame from camera")

    return frame


def frame_to_gray(frame, normalize=False):
    """
    Convierte un frame BGR a escala de grises.

    normalize=False -> uint8 rango [0, 255]
    normalize=True  -> float32 rango [0, 1]
    """

    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    if normalize:
        gray = gray.astype(np.float32) / 255.0

    return gray


def capture_gray_frame(cam, normalize=True):
    """
    Captura un frame y lo regresa en escala de grises.
    """

    frame = read_frame(cam)
    gray = frame_to_gray(frame, normalize=normalize)

    return gray


def show_live_frame(window_name, frame):
    """
    Muestra un frame en una ventana OpenCV.
    """

    cv.imshow(window_name, frame)


def get_key(delay=1):
    """
    Lee una tecla desde una ventana OpenCV.
    """

    return cv.waitKey(delay) & 0xFF


def release_camera(cam):
    """
    Libera la cámara y cierra ventanas OpenCV.
    """

    if cam is not None:
        cam.release()

    cv.destroyAllWindows()