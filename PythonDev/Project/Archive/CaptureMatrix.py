# Capturar matriz desde la cámara

import cv2


cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Windows

def SetCamera(cam):
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cam.isOpened():
        raise RuntimeError("Could not open camera")

# print("Press 's' to capture grayscale frame and print array")
# print("Press 'q' to quit")

def WarmUp(cam):
    for _ in range(10):
        cam.read()

def ConstantCapture(cam):
    while True:
        ret, frame = cam.read()
        if not ret:
            print("Failed to read frame")
            continue

        cv2.imshow("Live", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('s'):    
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            print("Shape:", gray.shape)
            print("Type:", type(gray))
            print(gray)
               

        if key == ord('q'):
            break


def main():
    SetCamera(cam)
    ConstantCapture(cam)
    cam.release()
    cv2.destroyAllWindows()