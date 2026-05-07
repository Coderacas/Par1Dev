import time
import cv2 as cv
import serial
from serial.tools import list_ports


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


BAUDRATE = 9600
ARDUINO_KEYWORDS = ("arduino", "ch340", "wch", "usb serial", "usb-serial")


def find_arduino_port():
    ports = list(list_ports.comports())

    for port in ports:
        description = f"{port.description} {port.manufacturer}".lower()
        if any(keyword in description for keyword in ARDUINO_KEYWORDS):
            return port.device

    if len(ports) == 1:
        return ports[0].device

    available_ports = ", ".join(port.device for port in ports) or "ninguno"
    raise RuntimeError(f"No se encontro Arduino. Puertos disponibles: {available_ports}")


def main():
    cam = None
    ser = None

    try:
        port = find_arduino_port()
        print(f"Arduino detectado en {port}.")

        cam = open_camera()
        set_camera(cam, width=640, height=480, buffer_size=1)
        warmup_camera(cam, frames=10)

        ser = serial.Serial(port, BAUDRATE, timeout=1)
        time.sleep(2)

        print(f"Esperando señales 's' desde Arduino en {port}...")

        while True:
            if ser.in_waiting > 0:
                dato = ser.read().decode("utf-8", errors="ignore").strip()

                if dato in ("a", "b", "c", "d", "e", "f"):
                    print("\nSeñal recibida. Capturando imagen...")

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

                    ser.write(b"k")
                    print("Se envió 'k' al Arduino.")

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

