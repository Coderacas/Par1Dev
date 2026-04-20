import time
import cv2 as cv
import serial

from camera_utils import (
    open_camera,
    set_camera,
    warmup_camera,
    capture_gray_frame,
    release_camera
)

from roi_utils import croptoroi
from features import basic_features
from glare import glare_stats


PUERTO = "COM4"
BAUDRATE = 9600


def main():
    cam = None
    ser = None

    try:
        cam = open_camera()
        set_camera(cam, width=640, height=480, buffer_size=1)
        warmup_camera(cam, frames=10)

        ser = serial.Serial(PUERTO, BAUDRATE, timeout=1)
        time.sleep(2)

        print(f"Esperando señales 's' desde Arduino en {PUERTO}...")

        while True:
            if ser.in_waiting > 0:
                dato = ser.read().decode("utf-8", errors="ignore").strip()

                if dato == "s":
                    print("\nSeñal 's' recibida. Capturando imagen...")

                    captured_gray = capture_gray_frame(cam, normalize=True)

                    x, y, w, h = 277, 54, 109, 112
                    im1mat = croptoroi(captured_gray, x, y, w, h)
                   
                    features = basic_features(im1mat)
                    glare = glare_stats(im1mat, bright_thr=0.98)

                    print("\n--- FEATURES ---")
                    for k, v in features.items():
                        print(f"{k}: {v}")

                    print("\n--- GLARE ---")
                    for k, v in glare.items():
                        print(f"{k}: {v}")

                    ser.write(b"b")
                    print("Se envió 'b' al Arduino.")

                elif dato == "q":
                    print("Señal 'q' recibida. Saliendo...")
                    break

            time.sleep(0.01)

    except serial.SerialException as e:
        print(f"Error serial: {e}")

    except Exception as e:
        print(f"Error general: {e}")

    finally:
        if ser is not None and ser.is_open:
            ser.close()
            print("Puerto serial cerrado.")

        if cam is not None:
            release_camera(cam)

        cv.destroyAllWindows()


if __name__ == "__main__":
    main()