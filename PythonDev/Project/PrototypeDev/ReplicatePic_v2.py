"""
ReplicatePic_v2_IN_PLACE_Z.py
────────────────────────────
Handshake con Arduino para inspección de pelotas.

Flujo automático:
  Arduino detecta A5 HIGH
    → manda "IN PLACE"
    → Python manda 'g' al Arduino
    → Arduino prende luces una por una
    → Python captura foto y manda 'k'
    → Arduino manda 'z' cuando ya terminó todas las fotos
    → Python clasifica
    → manda servo b/m
    → espera 0.5 s
    → manda 's' para steppers
    → al recibir STEPPERS_LISTOS:
        rota memoria
        vuelve a esperar "IN PLACE"

IMPORTANTE:
  Arduino debe mandar:
    Serial.write('z');
  cuando termine la secuencia de fotos.
"""

import os
import sys
import time
import queue
import random
import threading
import traceback

import numpy as np
import serial
from serial.tools import list_ports

from camera_utils  import open_camera, set_camera, warmup_camera, capture_gray_frame, release_camera
from roi_utils     import croptoroi
from features      import basic_features
from glare         import glare_stats


# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────
BAUDRATE = 9600

ROI_X, ROI_Y, ROI_W, ROI_H = 277, 54, 109, 112

NUM_ESTACIONES = 4
LUCES_POR_EST  = 4

SERVO_SETTLE_S    = 0.5
STEPPER_TIMEOUT_S = 30.0

ARDUINO_KEYWORDS = ("arduino", "ch340", "wch", "usb serial", "usb-serial")


# ─────────────────────────────────────────────────────────────
# FEATURES
# ─────────────────────────────────────────────────────────────
FEATURE_NAMES = [
    "mean_intensity", "std_intensity", "min_intensity", "max_intensity",
    "mean_grad",      "std_grad",      "max_grad",
    "mean_abs_lap",   "std_lap",
    "glare_pct",
]

N_FEATURES = len(FEATURE_NAMES)


def extraer_features(img_roi: np.ndarray) -> np.ndarray:
    """Imagen ROI -> vector de features brutas."""
    f = basic_features(img_roi)
    g = glare_stats(img_roi, bright_thr=0.98)

    vec = [
        f["mean_intensity"], f["std_intensity"],
        f["min_intensity"],  f["max_intensity"],
        f["mean_grad"],      f["std_grad"],       f["max_grad"],
        f["mean_abs_lap"],   f["std_lap"],
        g["glare_percentage"],
    ]

    return np.array(vec, dtype=np.float32)


def derivar_features(mat: np.ndarray) -> np.ndarray:
    """Matriz 4xN_FEATURES -> vector derivado para clasificador."""
    return np.concatenate([
        np.std(mat,  axis=0),
        np.mean(mat, axis=0),
        np.max(mat,  axis=0),
        np.min(mat,  axis=0),
    ])


def clasificar(vec_derivado: np.ndarray) -> bool:
    """
    Placeholder:
      True  = BUENA
      False = MALA

    Reemplazar después por modelo real:
      import joblib
      modelo = joblib.load("modelo.pkl")
      return bool(modelo.predict([vec_derivado])[0])
    """
    return random.choice([True, False])


# ─────────────────────────────────────────────────────────────
# LECTOR DE STDIN
# ─────────────────────────────────────────────────────────────
_stdin_queue: queue.Queue = queue.Queue()


def _stdin_worker():
    while True:
        try:
            linea = input()
            _stdin_queue.put(linea.strip().lower())
        except EOFError:
            break


def _leer_cmd() -> str:
    try:
        return _stdin_queue.get_nowait()
    except queue.Empty:
        return ""


# ─────────────────────────────────────────────────────────────
# UTILIDADES SERIAL
# ─────────────────────────────────────────────────────────────
def find_arduino_port() -> str:
    ports = list(list_ports.comports())

    for p in ports:
        desc = f"{p.description} {p.manufacturer or ''}".lower()
        if any(k in desc for k in ARDUINO_KEYWORDS):
            return p.device

    if len(ports) == 1:
        return ports[0].device

    available = ", ".join(p.device for p in ports) or "ninguno"
    raise RuntimeError(f"No se encontró Arduino. Puertos: {available}")


def decodificar_paso(byte_recibido: bytes):
    """
    Arduino manda:
      '1'-'9' para pasos 1-9
      'A'-'G' para pasos 10-16

    Devuelve:
      estacion, luz_en_estacion, paso_global
    """
    c = byte_recibido.decode("ascii", errors="ignore")

    if c.isdigit() and c != "0":
        paso = int(c)
    elif c.upper() in "ABCDEFG":
        paso = 10 + ord(c.upper()) - ord("A")
    else:
        return None

    paso_idx = paso - 1

    estacion        = paso_idx // LUCES_POR_EST
    luz_en_estacion = paso_idx % LUCES_POR_EST

    return estacion, luz_en_estacion, paso


def procesar_fotos_listas(ser, memoria):
    """
    Cuando Arduino manda 'z':
      - imprime clasificación final
      - decide servo según posición 4
      - manda b/m
      - espera
      - manda s para steppers
    """
    print("\n══ Clasificación final ══")

    for i, e in enumerate(memoria):
        estado_txt = "—" if e is None else ("BUENA" if e else "MALA")
        print(f"  Pelota {i + 1}: {estado_txt}")

    # Pelota en posición 4 es la que sale
    estado_pos4 = memoria[NUM_ESTACIONES - 1]

    # Si no hay dato, por seguridad la tratamos como mala
    if estado_pos4 is None:
        estado_pos4 = False

    # Servo antes de steppers
    cmd_servo = b"b" if estado_pos4 else b"m"

    print(
        f"\nServo: "
        f"{'derecha (BUENA)' if estado_pos4 else 'izquierda (MALA)'}"
    )

    ser.write(cmd_servo)
    time.sleep(SERVO_SETTLE_S)

    # Ahora sí: mandar steppers
    print("Enviando 's' al Arduino para mover steppers...")
    ser.reset_input_buffer()
    ser.write(b"s")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    t = threading.Thread(target=_stdin_worker, daemon=True)
    t.start()

    cam = None
    ser = None

    try:
        port = find_arduino_port()
        print(f"Arduino en {port}")

        cam = open_camera()
        set_camera(cam, width=640, height=480, buffer_size=1)
        warmup_camera(cam, frames=10)

        ser = serial.Serial(port, BAUDRATE, timeout=1)
        time.sleep(2)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        matrices = [
            np.zeros((LUCES_POR_EST, N_FEATURES), dtype=np.float32)
            for _ in range(NUM_ESTACIONES)
        ]

        memoria = [None] * NUM_ESTACIONES

        esperando_steppers = False
        t_inicio_steppers = None

        def reset_ciclo():
            nonlocal matrices, esperando_steppers, t_inicio_steppers

            matrices = [
                np.zeros((LUCES_POR_EST, N_FEATURES), dtype=np.float32)
                for _ in range(NUM_ESTACIONES)
            ]

            esperando_steppers = False
            t_inicio_steppers = None

        print("\nListo.")
        print("  Esperando IN PLACE desde Arduino")
        print("  Arduino debe mandar 'z' al terminar fotos")
        print("  salir → apagar y cerrar\n")

        while True:
            # ─────────────────────────────────────────────
            # COMANDOS DE TERMINAL
            # ─────────────────────────────────────────────
            cmd = _leer_cmd()

            if cmd == "salir":
                print("Saliendo. Mandando 'x' al Arduino...")
                ser.write(b"x")
                break

            # ─────────────────────────────────────────────
            # DATOS DEL ARDUINO
            # ─────────────────────────────────────────────
            if ser.in_waiting > 0:
                raw = ser.read(1)
                c = raw.decode("ascii", errors="ignore")

                # ─────────────────────────────────────
                # FIN DE FOTOS: Arduino manda 'z'
                # ─────────────────────────────────────
                if c == "z":
                    print("[Arduino] FOTOS_LISTAS")

                    procesar_fotos_listas(ser, memoria)

                    esperando_steppers = True
                    t_inicio_steppers = time.time()

                # ─────────────────────────────────────
                # PASOS DE LUZ: 1-9, A-G
                # ─────────────────────────────────────
                elif c in "123456789ABCDEFG":
                    decoded = decodificar_paso(raw)

                    if decoded is None:
                        continue

                    estacion, luz, paso = decoded

                    print(
                        f"[Paso {paso:02d}] "
                        f"Estación {estacion + 1}, cara {luz + 1} — capturando..."
                    )

                    gray = capture_gray_frame(cam, normalize=True)
                    roi  = croptoroi(gray, ROI_X, ROI_Y, ROI_W, ROI_H)
                    vec  = extraer_features(roi)

                    matrices[estacion][luz] = vec

                    print(f"  features: {vec.round(3)}")

                    # ACK para que Arduino avance a la siguiente luz
                    ser.write(b"k")

                    # Cuando termina las 4 caras de una estación, clasificar
                    if luz == LUCES_POR_EST - 1:
                        vec_rf = derivar_features(matrices[estacion])
                        resultado = clasificar(vec_rf)

                        if memoria[estacion] is None:
                            memoria[estacion] = resultado
                        else:
                            memoria[estacion] = memoria[estacion] and resultado

                        print(
                            f"  → Estación {estacion + 1}: "
                            f"{'BUENA' if memoria[estacion] else 'MALA'}"
                        )

                elif c in ("\r", "\n", ""):
                    pass

                else:
                    # Leer resto de línea de Arduino
                    rest = ser.read_until(b"\n").decode("ascii", errors="ignore").strip()
                    linea = (c + rest).strip()

                    if linea:
                        print(f"[Arduino] {linea}")

                    # ─────────────────────────────────────
                    # SENSOR IN PLACE → INICIAR CICLO
                    # ─────────────────────────────────────
                    if "IN PLACE" in linea:
                        if esperando_steppers:
                            print("IN PLACE recibido, pero todavía espero que terminen los steppers.")
                        else:
                            reset_ciclo()
                            ser.reset_input_buffer()
                            print("IN PLACE detectado. Enviando 'g' al Arduino para iniciar luces/fotos...")
                            ser.write(b"g")

                    # ─────────────────────────────────────
                    # FIN DE STEPPERS
                    # ─────────────────────────────────────
                    elif "STEPPERS_LISTOS" in linea:
                        esperando_steppers = False
                        t_inicio_steppers = None

                        # Rotar memoria:
                        # pos 4 sale, 3→4, 2→3, 1→2, nueva pos 1 = None
                        memoria.pop()
                        memoria.insert(0, None)

                        print("\nSteppers terminados.")
                        print("Memoria actualizada:")

                        for i, e in enumerate(memoria):
                            estado_txt = "—" if e is None else ("BUENA" if e else "MALA")
                            print(f"  Pos {i + 1}: {estado_txt}")

                        print("\nEsperando nuevo IN PLACE...")

                    elif "APAGADO" in linea:
                        esperando_steppers = False
                        t_inicio_steppers = None

            # ─────────────────────────────────────────────
            # TIMEOUT STEPPERS
            # ─────────────────────────────────────────────
            if esperando_steppers and t_inicio_steppers is not None:
                if time.time() - t_inicio_steppers > STEPPER_TIMEOUT_S:
                    print("WARNING: timeout esperando STEPPERS_LISTOS.")
                    print("Mandando 'x' por seguridad.")
                    ser.write(b"x")

                    esperando_steppers = False
                    t_inicio_steppers = None

            time.sleep(0.005)

    except serial.SerialException as e:
        print(f"Error serial: {e}")

    except KeyboardInterrupt:
        print("\nInterrumpido.")

    except Exception:
        traceback.print_exc()

    finally:
        if ser and ser.is_open:
            try:
                ser.write(b"x")
            except Exception:
                pass

            ser.close()
            print("Puerto serial cerrado.")

        if cam:
            release_camera(cam)


if __name__ == "__main__":
    main()