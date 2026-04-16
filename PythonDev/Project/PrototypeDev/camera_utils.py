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

# from camera_utils import (
#     open_camera,
#     set_camera,
#     warmup_camera,
#     read_frame,
#     frame_to_gray,
#     show_live_frame,
#     get_key,
#     release_camera
# )

# def main():
#     cam = open_camera()
#     set_camera(cam, width=640, height=480, buffer_size=1)
#     warmup_camera(cam, frames=10)

#     try:
#         while True:
#             frame = read_frame(cam)
#             show_live_frame("Live", frame)

#             key = get_key(1)

#             if key == ord('s'):
#                 gray = frame_to_gray(frame, normalize=True)
#                 print("Shape:", gray.shape)
#                 print("Type:", type(gray))
#                 print("Min/Max:", gray.min(), gray.max())

#             if key == ord('q'):
#                 break

#     finally:
#         release_camera(cam)

# if __name__ == "__main__":
#     main()