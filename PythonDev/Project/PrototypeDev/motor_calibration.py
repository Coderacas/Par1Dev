from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import cv2 as cv
import numpy as np


ROIBox = Tuple[int, int, int, int]


STATION_DETECTION_OVERRIDES = {
    1: {
        "expand_scale": 1.15,
        "min_circularity": 0.62,
        "min_radius_ratio": 0.28,
        "max_radius_ratio": 0.56,
        "hough_param2": 24,
        "min_centered_bonus": 0.35,
    },
    4: {
        "expand_scale": 1.15,
        "min_circularity": 0.62,
        "min_radius_ratio": 0.28,
        "max_radius_ratio": 0.56,
        "hough_param2": 24,
        "min_centered_bonus": 0.35,
    },
}


STATION_ERROR_AXES = {
    1: "x",
    2: "x",
    3: "y",
    4: "x",
}


@dataclass
class GeometryDetection:
    station: int
    ok: bool
    roi: ROIBox
    expanded_roi: ROIBox
    target_center: Tuple[float, float]
    center: Optional[Tuple[float, float]]
    error_px: Optional[Tuple[float, float]]
    radius: Optional[float]
    area: Optional[float]
    circularity: Optional[float]
    confidence: float
    reason: str = ""


@dataclass
class MotorCalibrationResult:
    ok: bool
    detections: List[GeometryDetection]
    mean_error_px: Optional[Tuple[float, float]]
    max_abs_error_px: Optional[Tuple[float, float]]


def filtrar_error_por_eje(station: int, error: Tuple[float, float]) -> Tuple[float, float]:
    axis = STATION_ERROR_AXES.get(station, "xy")

    if axis == "x":
        return float(error[0]), 0.0

    if axis == "y":
        return 0.0, float(error[1])

    return float(error[0]), float(error[1])


def expand_roi(roi: ROIBox, image_shape: Sequence[int], scale: float = 1.8) -> ROIBox:
    """Regresa un ROI mas grande, recortado a los bordes de la imagen."""
    x, y, w, h = roi
    img_h, img_w = image_shape[:2]

    cx = x + w / 2.0
    cy = y + h / 2.0
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))

    new_x = int(round(cx - new_w / 2.0))
    new_y = int(round(cy - new_h / 2.0))

    new_x = max(0, min(new_x, img_w - 1))
    new_y = max(0, min(new_y, img_h - 1))
    new_w = min(new_w, img_w - new_x)
    new_h = min(new_h, img_h - new_y)

    return new_x, new_y, new_w, new_h


def _to_gray_uint8(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 3:
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    else:
        gray = frame.copy()

    if gray.dtype == np.float32 or gray.dtype == np.float64:
        gray = np.clip(gray * 255.0, 0, 255).astype(np.uint8)
    elif gray.dtype != np.uint8:
        gray = cv.normalize(gray, None, 0, 255, cv.NORM_MINMAX).astype(np.uint8)

    return gray


def detectar_geometria_pelota(
    frame: np.ndarray,
    roi: ROIBox,
    station: int,
    expand_scale: float = 1.25,
    min_circularity: float = 0.45,
    min_radius_ratio: float = 0.24,
    max_radius_ratio: float = 0.62,
    hough_param2: int = 18,
    min_centered_bonus: float = 0.0,
) -> GeometryDetection:
    """
    Detecta la geometria de la pelota dentro de un ROI ampliado.

    El error se mide contra el centro del ROI original, no contra el ROI ampliado.
    Asi el ROI grande sirve para buscar, y el ROI original sirve como referencia.
    """
    station_overrides = STATION_DETECTION_OVERRIDES.get(station, {})
    expand_scale = station_overrides.get("expand_scale", expand_scale)
    min_circularity = station_overrides.get("min_circularity", min_circularity)
    min_radius_ratio = station_overrides.get("min_radius_ratio", min_radius_ratio)
    max_radius_ratio = station_overrides.get("max_radius_ratio", max_radius_ratio)
    hough_param2 = station_overrides.get("hough_param2", hough_param2)
    min_centered_bonus = station_overrides.get("min_centered_bonus", min_centered_bonus)

    gray = _to_gray_uint8(frame)
    x, y, w, h = roi
    expanded = expand_roi(roi, gray.shape, scale=expand_scale)
    ex, ey, ew, eh = expanded

    target = (x + w / 2.0, y + h / 2.0)
    crop = gray[ey:ey + eh, ex:ex + ew]

    if crop.size == 0:
        return GeometryDetection(
            station=station,
            ok=False,
            roi=roi,
            expanded_roi=expanded,
            target_center=target,
            center=None,
            error_px=None,
            radius=None,
            area=None,
            circularity=None,
            confidence=0.0,
            reason="ROI ampliado vacio",
        )

    min_dim = min(ew, eh)
    min_radius = min_dim * min_radius_ratio
    max_radius = min_dim * max_radius_ratio

    best = None
    best_score = -1.0

    blur = cv.GaussianBlur(crop, (5, 5), 0)
    threshold_modes = (
        cv.THRESH_BINARY + cv.THRESH_OTSU,
        cv.THRESH_BINARY_INV + cv.THRESH_OTSU,
    )

    for threshold_mode in threshold_modes:
        _, mask_otsu = cv.threshold(blur, 0, 255, threshold_mode)

        kernel = np.ones((3, 3), np.uint8)
        mask = cv.morphologyEx(mask_otsu, cv.MORPH_OPEN, kernel, iterations=1)
        mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = float(cv.contourArea(contour))
            if area <= 0:
                continue

            perimeter = float(cv.arcLength(contour, True))
            if perimeter <= 0:
                continue

            (cx_local, cy_local), radius = cv.minEnclosingCircle(contour)
            if radius < min_radius or radius > max_radius:
                continue

            circularity = float(4.0 * np.pi * area / (perimeter * perimeter))
            if circularity < min_circularity:
                continue

            fill_ratio = area / (np.pi * radius * radius)
            centered_bonus = 1.0 - min(
                1.0,
                np.hypot(cx_local - ew / 2.0, cy_local - eh / 2.0) / max(1.0, min_dim),
            )
            if centered_bonus < min_centered_bonus:
                continue

            score = (0.55 * circularity) + (0.25 * fill_ratio) + (0.20 * centered_bonus)

            if score > best_score:
                best_score = score
                best = (cx_local, cy_local, radius, area, circularity, score)

    if best is None:
        circles = cv.HoughCircles(
            blur,
            cv.HOUGH_GRADIENT,
            dp=1.2,
            minDist=max(12, min_dim // 2),
            param1=70,
            param2=hough_param2,
            minRadius=max(3, int(round(min_radius))),
            maxRadius=max(4, int(round(max_radius))),
        )

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for cx_local, cy_local, radius in circles:
                if not (0 <= cx_local < ew and 0 <= cy_local < eh):
                    continue

                centered_bonus = 1.0 - min(
                    1.0,
                    np.hypot(cx_local - ew / 2.0, cy_local - eh / 2.0) / max(1.0, min_dim),
                )
                if centered_bonus < min_centered_bonus:
                    continue

                area = float(np.pi * radius * radius)
                circularity = 1.0
                score = 0.70 + (0.30 * centered_bonus)

                if score > best_score:
                    best_score = score
                    best = (
                        float(cx_local),
                        float(cy_local),
                        float(radius),
                        area,
                        circularity,
                        score,
                    )

    if best is None:
        return GeometryDetection(
            station=station,
            ok=False,
            roi=roi,
            expanded_roi=expanded,
            target_center=target,
            center=None,
            error_px=None,
            radius=None,
            area=None,
            circularity=None,
            confidence=0.0,
            reason="Sin geometria circular suficiente",
        )

    cx_local, cy_local, radius, area, circularity, confidence = best
    center = (ex + float(cx_local), ey + float(cy_local))
    error = filtrar_error_por_eje(station, (center[0] - target[0], center[1] - target[1]))

    return GeometryDetection(
        station=station,
        ok=True,
        roi=roi,
        expanded_roi=expanded,
        target_center=target,
        center=center,
        error_px=error,
        radius=float(radius),
        area=float(area),
        circularity=float(circularity),
        confidence=float(max(0.0, min(confidence, 1.0))),
    )


def calibrar_motores(
    frame: np.ndarray,
    rois: Iterable[ROIBox],
    expand_scale: float = 1.25,
    tolerance_px: float = 8.0,
) -> MotorCalibrationResult:
    """
    Analiza los ROIs ampliados y calcula el desfase visual de cada estacion.

    Esta funcion todavia no mueve motores. Primero sirve para validar que la
    geometria se detecta bien y que el error en pixeles tiene sentido.
    """
    detections = [
        detectar_geometria_pelota(
            frame=frame,
            roi=roi,
            station=i + 1,
            expand_scale=expand_scale,
        )
        for i, roi in enumerate(rois)
    ]

    valid_errors = np.array(
        [d.error_px for d in detections if d.ok and d.error_px is not None],
        dtype=np.float32,
    )

    if len(valid_errors) == 0:
        return MotorCalibrationResult(
            ok=False,
            detections=detections,
            mean_error_px=None,
            max_abs_error_px=None,
        )

    mean_error = tuple(np.mean(valid_errors, axis=0).astype(float))
    max_abs_error = tuple(np.max(np.abs(valid_errors), axis=0).astype(float))
    all_detected = all(d.ok for d in detections)
    inside_tolerance = all(
        d.error_px is not None
        and abs(d.error_px[0]) <= tolerance_px
        and abs(d.error_px[1]) <= tolerance_px
        for d in detections
    )

    return MotorCalibrationResult(
        ok=all_detected and inside_tolerance,
        detections=detections,
        mean_error_px=mean_error,
        max_abs_error_px=max_abs_error,
    )


def calibrar_motores_con_fotos(
    frames_por_estacion: Sequence[np.ndarray],
    rois: Sequence[ROIBox],
    expand_scale: float = 1.25,
    tolerance_px: float = 8.0,
) -> MotorCalibrationResult:
    """
    Analiza una foto por estacion.

    Se usa cuando Arduino prende la primera luz de cada estacion y Python
    captura 4 fotos independientes en vez de una sola foto global.
    """
    detections = []

    for i, roi in enumerate(rois):
        if i >= len(frames_por_estacion) or frames_por_estacion[i] is None:
            x, y, w, h = roi
            detections.append(
                GeometryDetection(
                    station=i + 1,
                    ok=False,
                    roi=roi,
                    expanded_roi=roi,
                    target_center=(x + w / 2.0, y + h / 2.0),
                    center=None,
                    error_px=None,
                    radius=None,
                    area=None,
                    circularity=None,
                    confidence=0.0,
                    reason="Sin foto para esta estacion",
                )
            )
            continue

        detections.append(
            detectar_geometria_pelota(
                frame=frames_por_estacion[i],
                roi=roi,
                station=i + 1,
                expand_scale=expand_scale,
            )
        )

    valid_errors = np.array(
        [d.error_px for d in detections if d.ok and d.error_px is not None],
        dtype=np.float32,
    )

    if len(valid_errors) == 0:
        return MotorCalibrationResult(
            ok=False,
            detections=detections,
            mean_error_px=None,
            max_abs_error_px=None,
        )

    mean_error = tuple(np.mean(valid_errors, axis=0).astype(float))
    max_abs_error = tuple(np.max(np.abs(valid_errors), axis=0).astype(float))
    all_detected = all(d.ok for d in detections)
    inside_tolerance = all(
        d.error_px is not None
        and abs(d.error_px[0]) <= tolerance_px
        and abs(d.error_px[1]) <= tolerance_px
        for d in detections
    )

    return MotorCalibrationResult(
        ok=all_detected and inside_tolerance,
        detections=detections,
        mean_error_px=mean_error,
        max_abs_error_px=max_abs_error,
    )


def imprimir_resultado_calibracion(result: MotorCalibrationResult) -> None:
    print("\n=== Calibracion visual de motores ===")

    for d in result.detections:
        if d.station > 3:
            continue

        if not d.ok:
            print(f"  Estacion {d.station}: SIN DETECCION ({d.reason})")
            continue

        ex, ey = d.error_px
        cx, cy = d.center
        axis = STATION_ERROR_AXES.get(d.station, "xy")
        print(
            f"  Estacion {d.station}: "
            f"eje={axis} "
            f"centro=({cx:.1f}, {cy:.1f}) "
            f"error=({ex:+.1f}, {ey:+.1f}) px "
            f"radio={d.radius:.1f} "
            f"circ={d.circularity:.2f} "
            f"conf={d.confidence:.2f}"
        )

    if result.mean_error_px is None:
        print("  Resultado: no hay geometria suficiente para corregir.")
        return

    mx, my = result.mean_error_px
    ax, ay = result.max_abs_error_px
    print(f"  Error promedio: ({mx:+.1f}, {my:+.1f}) px")
    print(f"  Error maximo abs: ({ax:.1f}, {ay:.1f}) px")
    print(f"  Dentro de tolerancia: {'SI' if result.ok else 'NO'}")


def dibujar_resultado_calibracion(
    frame: np.ndarray,
    result: MotorCalibrationResult,
) -> np.ndarray:
    """
    Dibuja ROIs, geometria detectada y error visual sobre una copia del frame.

    Colores:
      azul   = ROI original esperado
      amarillo = ROI ampliado usado para buscar
      verde  = pelota detectada
      rojo   = centro esperado
      magenta = centro detectado y flecha de error
    """
    if frame.ndim == 2:
        if frame.dtype != np.uint8:
            gray = _to_gray_uint8(frame)
        else:
            gray = frame
        annotated = cv.cvtColor(gray, cv.COLOR_GRAY2BGR)
    else:
        annotated = frame.copy()

    for d in result.detections:
        x, y, w, h = d.roi
        ex, ey, ew, eh = d.expanded_roi
        tx, ty = d.target_center

        cv.rectangle(annotated, (ex, ey), (ex + ew, ey + eh), (0, 255, 255), 1)
        cv.rectangle(annotated, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv.drawMarker(
            annotated,
            (int(round(tx)), int(round(ty))),
            (0, 0, 255),
            markerType=cv.MARKER_CROSS,
            markerSize=16,
            thickness=2,
        )

        label_origin = (x, max(18, y - 8))

        if d.ok and d.center is not None and d.radius is not None:
            cx, cy = d.center
            center_i = (int(round(cx)), int(round(cy)))
            target_i = (int(round(tx)), int(round(ty)))

            cv.circle(annotated, center_i, int(round(d.radius)), (0, 180, 0), 2)
            cv.circle(annotated, center_i, 3, (255, 0, 255), -1)
            cv.arrowedLine(
                annotated,
                target_i,
                center_i,
                (255, 0, 255),
                2,
                tipLength=0.18,
            )

            err_x, err_y = d.error_px
            label = f"E{d.station} dx={err_x:+.0f} dy={err_y:+.0f} r={d.radius:.0f}"
            label_color = (0, 180, 0)
        else:
            label = f"E{d.station} sin deteccion"
            label_color = (0, 0, 255)

        cv.putText(
            annotated,
            label,
            label_origin,
            cv.FONT_HERSHEY_SIMPLEX,
            0.45,
            label_color,
            1,
            cv.LINE_AA,
        )

    return annotated


def mostrar_resultado_calibracion(
    frame: np.ndarray,
    result: MotorCalibrationResult,
    window_name: str = "Calibracion motores",
) -> np.ndarray:
    """Muestra la imagen anotada y tambien la regresa por si se quiere guardar."""
    annotated = dibujar_resultado_calibracion(frame, result)
    cv.imshow(window_name, annotated)
    cv.waitKey(1)
    return annotated


def mostrar_recortes_calibracion(
    frame: np.ndarray,
    result: MotorCalibrationResult,
    window_name: str = "ROIs calibracion",
) -> Optional[np.ndarray]:
    """Muestra una cuadricula con los ROIs ampliados que usa el detector."""
    if not result.detections:
        return None

    display = _to_gray_uint8(frame)
    crops = []

    for d in result.detections:
        ex, ey, ew, eh = d.expanded_roi
        crop = cv.cvtColor(display[ey:ey + eh, ex:ex + ew], cv.COLOR_GRAY2BGR)

        if d.ok and d.center is not None and d.radius is not None:
            cx = int(round(d.center[0] - ex))
            cy = int(round(d.center[1] - ey))
            cv.circle(crop, (cx, cy), int(round(d.radius)), (0, 180, 0), 2)
            cv.circle(crop, (cx, cy), 3, (255, 0, 255), -1)
            label = f"E{d.station} OK"
            color = (0, 180, 0)
        else:
            label = f"E{d.station} NO"
            color = (0, 0, 255)

        cv.putText(crop, label, (6, 18), cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv.LINE_AA)
        crops.append(crop)

    max_h = max(c.shape[0] for c in crops)
    max_w = max(c.shape[1] for c in crops)
    padded = []

    for crop in crops:
        canvas = np.zeros((max_h, max_w, 3), dtype=np.uint8)
        canvas[:crop.shape[0], :crop.shape[1]] = crop
        padded.append(canvas)

    grid = np.hstack(padded)

    cv.imshow(window_name, grid)
    cv.waitKey(1)
    return grid


def mostrar_fotos_calibracion(
    frames_por_estacion: Sequence[np.ndarray],
    result: MotorCalibrationResult,
    window_name: str = "Fotos calibracion",
) -> Optional[np.ndarray]:
    """Muestra las 4 fotos de calibracion anotadas, una por estacion."""
    annotated_frames = []

    for d in result.detections:
        idx = d.station - 1

        if idx >= len(frames_por_estacion) or frames_por_estacion[idx] is None:
            continue

        single_result = MotorCalibrationResult(
            ok=d.ok,
            detections=[d],
            mean_error_px=d.error_px,
            max_abs_error_px=(
                (abs(d.error_px[0]), abs(d.error_px[1]))
                if d.error_px is not None
                else None
            ),
        )
        annotated_frames.append(dibujar_resultado_calibracion(frames_por_estacion[idx], single_result))

    if not annotated_frames:
        return None

    target_w = 320
    target_h = 240
    resized = [cv.resize(frame, (target_w, target_h)) for frame in annotated_frames]

    while len(resized) < 4:
        resized.append(np.zeros((target_h, target_w, 3), dtype=np.uint8))

    top = np.hstack(resized[:2])
    bottom = np.hstack(resized[2:4])
    grid = np.vstack([top, bottom])

    cv.imshow(window_name, grid)
    cv.waitKey(1)
    return grid


def mostrar_recortes_calibracion_con_fotos(
    frames_por_estacion: Sequence[np.ndarray],
    result: MotorCalibrationResult,
    window_name: str = "ROIs calibracion",
) -> Optional[np.ndarray]:
    """Muestra solo el ROI ampliado de cada foto de calibracion."""
    crops = []

    for d in result.detections:
        if d.station > 3:
            continue

        idx = d.station - 1

        if idx >= len(frames_por_estacion) or frames_por_estacion[idx] is None:
            placeholder = np.zeros((140, 140, 3), dtype=np.uint8)
            cv.putText(
                placeholder,
                f"E{d.station} sin foto",
                (8, 70),
                cv.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 255),
                1,
                cv.LINE_AA,
            )
            crops.append(placeholder)
            continue

        frame = frames_por_estacion[idx]
        if frame.ndim == 2:
            display = cv.cvtColor(_to_gray_uint8(frame), cv.COLOR_GRAY2BGR)
        else:
            display = frame.copy()

        ex, ey, ew, eh = d.expanded_roi
        crop = display[ey:ey + eh, ex:ex + ew].copy()

        if crop.size == 0:
            placeholder = np.zeros((140, 140, 3), dtype=np.uint8)
            cv.putText(
                placeholder,
                f"E{d.station} ROI vacio",
                (8, 70),
                cv.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 255),
                1,
                cv.LINE_AA,
            )
            crops.append(placeholder)
            continue

        if d.ok and d.center is not None and d.radius is not None:
            cx = int(round(d.center[0] - ex))
            cy = int(round(d.center[1] - ey))
            tx = int(round(d.target_center[0] - ex))
            ty = int(round(d.target_center[1] - ey))
            err_x, err_y = d.error_px
            error_end = (
                int(round(d.target_center[0] + err_x - ex)),
                int(round(d.target_center[1] + err_y - ey)),
            )

            cv.circle(crop, (cx, cy), int(round(d.radius)), (0, 180, 0), 2)
            cv.circle(crop, (cx, cy), 3, (255, 0, 255), -1)
            cv.drawMarker(
                crop,
                (tx, ty),
                (0, 0, 255),
                markerType=cv.MARKER_CROSS,
                markerSize=14,
                thickness=2,
            )
            cv.arrowedLine(
                crop,
                (tx, ty),
                error_end,
                (255, 0, 255),
                2,
                tipLength=0.20,
            )
            label = f"E{d.station} OK"
            color = (0, 180, 0)
        else:
            label = f"E{d.station} NO"
            color = (0, 0, 255)

        cv.putText(crop, label, (6, 18), cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv.LINE_AA)
        crops.append(crop)

    if not crops:
        return None

    max_h = max(c.shape[0] for c in crops)
    max_w = max(c.shape[1] for c in crops)
    padded = []

    for crop in crops:
        canvas = np.zeros((max_h, max_w, 3), dtype=np.uint8)
        canvas[:crop.shape[0], :crop.shape[1]] = crop
        padded.append(canvas)

    while len(padded) < 4:
        padded.append(np.zeros((max_h, max_w, 3), dtype=np.uint8))

    top = np.hstack(padded[:2])
    bottom = np.hstack(padded[2:4])
    grid = np.vstack([top, bottom])

    cv.imshow(window_name, grid)
    cv.waitKey(1)
    return grid


def crear_overlay_fotos_calibracion(
    frames_por_estacion: Sequence[np.ndarray],
    alpha: float = 0.35,
) -> Optional[np.ndarray]:
    """Superpone las fotos de calibracion con transparencia, sin tintes artificiales."""
    valid_frames = [frame for frame in frames_por_estacion if frame is not None]

    if not valid_frames:
        return None

    base_shape = valid_frames[0].shape[:2]
    overlay = np.zeros((base_shape[0], base_shape[1], 3), dtype=np.float32)
    total_weight = 0.0

    for frame in frames_por_estacion:
        if frame is None:
            continue

        if frame.ndim == 2:
            display = cv.cvtColor(_to_gray_uint8(frame), cv.COLOR_GRAY2BGR)
        else:
            display = frame.copy()

        if display.shape[:2] != base_shape:
            display = cv.resize(display, (base_shape[1], base_shape[0]))

        overlay += display.astype(np.float32) * alpha
        total_weight += alpha

    if total_weight <= 0:
        return None

    overlay = np.clip(overlay / total_weight, 0, 255).astype(np.uint8)
    return overlay


def mostrar_overlay_fotos_calibracion(
    frames_por_estacion: Sequence[np.ndarray],
    result: Optional[MotorCalibrationResult] = None,
    window_name: str = "Overlay calibracion",
    alpha: float = 0.35,
) -> Optional[np.ndarray]:
    """Muestra las cuatro fotos una sobre otra con transparencia."""
    overlay = crear_overlay_fotos_calibracion(frames_por_estacion, alpha=alpha)

    if overlay is None:
        return None

    if result is not None:
        for d in result.detections:
            color = (255, 255, 255)
            x, y, w, h = d.roi
            cv.rectangle(overlay, (x, y), (x + w, y + h), color, 1)

            if d.ok and d.center is not None and d.radius is not None:
                cx, cy = d.center
                center_i = (int(round(cx)), int(round(cy)))
                cv.circle(overlay, center_i, int(round(d.radius)), color, 2)
                cv.circle(overlay, center_i, 3, color, -1)

            cv.putText(
                overlay,
                f"E{d.station}",
                (x, max(18, y - 6)),
                cv.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv.LINE_AA,
            )

    cv.imshow(window_name, overlay)
    cv.waitKey(1)
    return overlay
