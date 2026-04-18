from camera_utils import (
    open_camera,
    set_camera,
    warmup_camera,
    read_frame,
    capture_gray_frame,
    show_live_frame,
    get_key,
    release_camera
)

from roi_utils import ROI, croptoroi
from features import basic_features
from glare import glare_stats

def main():
    cam = open_camera()
    set_camera(cam, width=640, height=480, buffer_size=1)
    warmup_camera(cam, frames=10)

    captured_gray = None

    try:
        while True:
            frame = read_frame(cam)
            show_live_frame("Live", frame)

            key = get_key(1)

            if key == ord('s'):
                captured_gray = capture_gray_frame(cam, normalize=True)
                print("Shape:", captured_gray.shape)
                print("Type:", type(captured_gray))
                print("Min/Max:", captured_gray.min(), captured_gray.max())
                break

            if key == ord('q'):
                break

    finally:
        release_camera(cam)

    if captured_gray is None:
        print("No se capturó ninguna imagen.")
        return

    x, y, w, h = ROI(captured_gray)
    im1mat = croptoroi(captured_gray, x, y, w, h)

    features = basic_features(im1mat)
    glare = glare_stats(im1mat, bright_thr=0.98)

    print("\n--- FEATURES ---")
    for k, v in features.items():
        print(f"{k}: {v}")

    print("\n--- GLARE ---")
    for k, v in glare.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()