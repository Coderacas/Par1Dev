from image_io import cargarimagen
from roi_utils import ROI, croptoroi
from features import basic_features
from glare import glare_stats

def main():
    fold = 'Polight'
    imgname = 'PolarizedProG.jpeg'

    img = cargarimagen(fold, imgname)

    x, y, w, h = ROI(img)
    im1mat = croptoroi(img, x, y, w, h)

    features = basic_features(im1mat)
    glare = glare_stats(im1mat, bright_thr=0.98)

    for k, v in features.items():
        print(f"{k}: {v}")

    print("\n--- GLARE ---")
    for k, v in glare.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()