import queue
import threading
import time
import traceback

import numpy as np
import serial

from camera_utils import open_camera, read_frame, release_camera, set_camera, warmup_camera
from main import BAUDRATE, NUM_ESTACIONES, ROIS_POR_ESTACION, decodificar_paso, find_arduino_port
from motor_calibration import (
    calibrar_motores_con_fotos,
    imprimir_resultado_calibracion,
    mostrar_recortes_calibracion_con_fotos,
)


LIGHT_VISIBLE_S = 0.01
CAPTURE_SETTLE_S = 0.04
CAPTURE_FLUSH_FRAMES = 0
CAPTURE_FLUSH_DELAY_S = 0.0
ERROR_THRESHOLD_PX = 6.0
STEPS_PER_PIXEL = 0.5
MIN_CORRECTION_STEPS = 2
MAX_CORRECTION_STEPS = 30

CORRECTION_PARAMS_BY_STATION = {
    1: {
        "threshold_px": 6.0,
        "steps_per_pixel": 9.0,
        "min_steps": 18,
        "max_steps": 220,
    },
    2: {
        "threshold_px": 3.0,
        "steps_per_pixel": 5.9,
        "min_steps": 18,
        "max_steps": 220,
    },
    3: {
        "threshold_px": 6.0,
        "steps_per_pixel": 8.8,
        "min_steps": 18,
        "extra_steps": 0,
        "max_steps": 220,
    },
    4: {
        "threshold_px": 6.0,
        "steps_per_pixel": 9.0,
        "min_steps": 18,
        "max_steps": 220,
    },
}

CORRECTION_AXIS_BY_STATION = {
    1: "x",
    2: "x",
    3: "y",
    4: "x",
}

# Cambia el signo si un motor corrige al reves.
CORRECTION_SIGN_BY_STATION = {
    1: 1,
    2: 1,
    3: 1,
    4: 1,
}

LUCES_POR_ESTACION = 4


_stdin_queue = queue.Queue()


def _stdin_worker():
    while True:
        try:
            _stdin_queue.put(input().strip().lower())
        except EOFError:
            break


def _leer_cmd():
    try:
        return _stdin_queue.get_nowait()
    except queue.Empty:
        return ""


def calcular_steps_correccion(station, error_px):
    params = CORRECTION_PARAMS_BY_STATION.get(station, {})
    threshold_px = params.get("threshold_px", ERROR_THRESHOLD_PX)
    steps_per_pixel = params.get("steps_per_pixel", STEPS_PER_PIXEL)
    min_steps = params.get("min_steps", MIN_CORRECTION_STEPS)
    max_steps = params.get("max_steps", MAX_CORRECTION_STEPS)
    extra_steps = params.get("extra_steps", 0)

    magnitude = abs(float(error_px))

    if magnitude < threshold_px:
        return 0

    steps = int(round(magnitude * steps_per_pixel)) + extra_steps
    steps = max(min_steps, min(max_steps, steps))
    return steps


def combinar_fotos_estacion(frames_luces):
    if len(frames_luces) < LUCES_POR_ESTACION:
        return None

    if any(frame is None for frame in frames_luces[:LUCES_POR_ESTACION]):
        return None

    base_h, base_w = frames_luces[0].shape[:2]
    normalized = []

    for frame in frames_luces[:LUCES_POR_ESTACION]:
        if frame.shape[:2] != (base_h, base_w):
            return None

        normalized.append(frame.astype(np.float32))

    combined = np.zeros_like(normalized[0], dtype=np.float32)

    for frame in normalized:
        combined += frame * 0.25

    return np.clip(combined, 0, 255).astype(np.uint8)


def combinar_fotos_calibracion(frames_por_luz):
    return [combinar_fotos_estacion(frames_luces) for frames_luces in frames_por_luz]


def capturar_frame_con_luz(cam):
    time.sleep(LIGHT_VISIBLE_S)
    time.sleep(CAPTURE_SETTLE_S)

    frame = None
    for _ in range(CAPTURE_FLUSH_FRAMES):
        frame = read_frame(cam)
        time.sleep(CAPTURE_FLUSH_DELAY_S)

    return read_frame(cam) if frame is not None else read_frame(cam)


def esperar_respuesta_correccion(ser, timeout_s=8.0):
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        if ser.in_waiting > 0:
            line = ser.readline().decode("ascii", errors="ignore").strip()
            if line:
                print(f"[Arduino] {line}")
                if "CORRECCION_LISTA" in line or "CORRECCION_INVALIDA" in line:
                    return line

        time.sleep(0.01)

    print("WARNING: timeout esperando respuesta de correccion.")
    return ""


def enviar_correcciones(ser, result):
    print("\n=== Correcciones Arduino ===")
    any_sent = False

    for detection in result.detections:
        station = detection.station

        if station not in CORRECTION_AXIS_BY_STATION:
            continue

        if not detection.ok or detection.error_px is None:
            print(f"  E{station}: sin deteccion, no corrijo.")
            continue

        axis = CORRECTION_AXIS_BY_STATION[station]
        error_value = detection.error_px[0] if axis == "x" else detection.error_px[1]
        steps = calcular_steps_correccion(station, error_value)

        if steps == 0:
            print(f"  E{station}: error {axis}={error_value:+.1f}px dentro de umbral.")
            continue

        direction = 1 if error_value > 0 else -1
        signed_steps = direction * steps * CORRECTION_SIGN_BY_STATION[station]
        command = f"R {station} {signed_steps}\n"

        print(
            f"  E{station}: error {axis}={error_value:+.1f}px "
            f"-> motor {station}, steps {signed_steps:+d}"
        )
        ser.write(command.encode("ascii"))
        esperar_respuesta_correccion(ser)
        any_sent = True

    if not any_sent:
        print("  Sin correcciones necesarias.")


def main():
    threading.Thread(target=_stdin_worker, daemon=True).start()

    cam = None
    ser = None
    frames_calibracion = [None] * NUM_ESTACIONES
    frames_calibracion_por_luz = [
        [None] * LUCES_POR_ESTACION for _ in range(NUM_ESTACIONES)
    ]
    calibrando = False
    in_place_detectado = False

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

        print("\nCalibracion independiente de motores con vision.")
        print("Este script NO clasifica y NO mueve servo.")
        print("1. Coloca la pelota.")
        print("2. Escribe calibrar para capturar L1-L4 por estacion.")
        print("3. Se superponen L1-L4 con 25% cada una, simulando 4 luces encendidas.")
        print("4. Escribe salir para cerrar.\n")

        while True:
            cmd = _leer_cmd()

            if cmd in ("salir", "q", "exit"):
                print("Saliendo. Apagando luces internas...")
                ser.write(b"o")
                break

            if cmd == "calibrar":
                print("Iniciando calibracion con luces: enviando 'g'.")
                frames_calibracion = [None] * NUM_ESTACIONES
                frames_calibracion_por_luz = [
                    [None] * LUCES_POR_ESTACION for _ in range(NUM_ESTACIONES)
                ]
                calibrando = True
                ser.reset_input_buffer()
                ser.write(b"g")
                continue

            if ser.in_waiting <= 0:
                time.sleep(0.005)
                continue

            raw = ser.read(1)
            c = raw.decode("ascii", errors="ignore")

            if c == "z":
                if not calibrando:
                    print("[Arduino] z recibido fuera de calibracion. Apagando luces.")
                    ser.write(b"o")
                    continue

                print("[Arduino] Fotos de calibracion listas.")
                frames_calibracion = combinar_fotos_calibracion(frames_calibracion_por_luz)
                faltantes = [
                    idx + 1
                    for idx, frame in enumerate(frames_calibracion)
                    if frame is None
                ]
                if faltantes:
                    print(
                        "Faltaron fotos de calibracion en: "
                        + ", ".join(f"E{idx}" for idx in faltantes)
                    )
                    calibrando = False
                    ser.write(b"o")
                    continue

                resultado = calibrar_motores_con_fotos(
                    frames_calibracion,
                    ROIS_POR_ESTACION,
                    expand_scale=1.25,
                    tolerance_px=8.0,
                )
                imprimir_resultado_calibracion(resultado)
                mostrar_recortes_calibracion_con_fotos(frames_calibracion, resultado)
                enviar_correcciones(ser, resultado)

                calibrando = False
                in_place_detectado = False
                ser.write(b"o")
                print("\nListo. Puedes meter otra pelota y escribir calibrar otra vez.")
                continue

            decoded = decodificar_paso(raw)
            if decoded is not None:
                estacion, luz, paso = decoded

                if not calibrando:
                    print(f"[Arduino] Paso {paso:02d} recibido fuera de calibracion. ACK seguro.")
                    ser.write(b"k")
                    continue

                if 0 <= estacion < NUM_ESTACIONES and 0 <= luz < LUCES_POR_ESTACION:
                    print(
                        f"[Calibracion] Capturando E{estacion + 1} "
                        f"L{luz + 1} (paso {paso:02d})"
                    )
                    frames_calibracion_por_luz[estacion][luz] = capturar_frame_con_luz(cam)
                else:
                    print(
                        f"[Calibracion] Paso fuera de rango E{estacion + 1} "
                        f"L{luz + 1} (ACK)"
                    )
                    time.sleep(LIGHT_VISIBLE_S)

                ser.write(b"k")
                continue

            if c in ("\r", "\n", ""):
                continue

            rest = ser.read_until(b"\n").decode("ascii", errors="ignore").strip()
            linea = (c + rest).strip()

            if not linea:
                continue

            print(f"[Arduino] {linea}")

            if "IN PLACE" in linea:
                in_place_detectado = True
                print("IN PLACE detectado. Escribe calibrar para iniciar captura con luces.")

            elif "APAGADO" in linea or "LISTO" in linea:
                calibrando = False

    except KeyboardInterrupt:
        print("\nInterrumpido.")

    except Exception:
        traceback.print_exc()

    finally:
        if ser and ser.is_open:
            try:
                ser.write(b"o")
            except Exception:
                pass
            ser.close()
            print("Puerto serial cerrado.")

        if cam:
            release_camera(cam)


if __name__ == "__main__":
    main()
