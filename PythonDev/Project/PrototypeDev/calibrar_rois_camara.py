import cv2 as cv

from camera_utils import (
    open_camera,
    set_camera,
    warmup_camera,
    read_frame,
    show_live_frame,
    get_key,
    release_camera,
)
from roi_utils import ROI


NUM_ESTACIONES = 4


def dibujar_rois(img, rois):
    preview = img.copy()

    for idx, (x, y, w, h) in enumerate(rois, start=1):
        cv.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv.putText(
            preview,
            f"E{idx}",
            (x, max(20, y - 8)),
            cv.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv.LINE_AA,
        )

    return preview


def imprimir_rois_para_main(rois):
    print("\nROIS_POR_ESTACION = [")
    for idx, roi in enumerate(rois, start=1):
        print(f"    {roi},  # Estacion {idx}")
    print("]")


def capturar_frame():
    cam = open_camera()
    set_camera(cam, width=640, height=480, buffer_size=1)
    warmup_camera(cam, frames=10)

    try:
        while True:
            frame = read_frame(cam)
            show_live_frame("Camara - s=capturar, q=salir", frame)

            key = get_key(1)

            if key == ord("s"):
                return frame.copy()

            if key == ord("q"):
                return None
    finally:
        release_camera(cam)


def main():
    frame = capturar_frame()

    if frame is None:
        print("No se capturo ninguna imagen.")
        return

    rois = []

    for estacion in range(1, NUM_ESTACIONES + 1):
        print(f"\nSelecciona ROI de estacion {estacion}.")
        print("Arrastra con el mouse y confirma con ENTER o SPACE.")

        x, y, w, h = ROI(frame)

        if w == 0 or h == 0:
            print("ROI cancelada o vacia. Intenta de nuevo.")
            return

        rois.append((x, y, w, h))

        preview = dibujar_rois(frame, rois)
        cv.imshow("ROIs seleccionadas", preview)
        cv.waitKey(500)

    imprimir_rois_para_main(rois)

    preview = dibujar_rois(frame, rois)
    cv.imshow("ROIs finales - presiona cualquier tecla", preview)
    cv.waitKey(0)
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
