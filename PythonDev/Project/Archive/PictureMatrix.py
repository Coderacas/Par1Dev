#Este código ya utiliza una imagen caputrada para tomar dos ROIs con una sola calibración

import cv2 as cv
import sys
import numpy as np
import os

np.set_printoptions(threshold=sys.maxsize)

def cargarimagen(FolderPhotos,NombreImagen):
    current_dir = os.path.dirname(os.path.abspath(__file__))   # .../PythonDev/Project/PrototypeDev
    project_dir = os.path.dirname(current_dir)                 # .../PythonDev/Project
    pythondev_dir = os.path.dirname(project_dir)               # .../PythonDev
    repo_dir = os.path.dirname(pythondev_dir)                  # .../Par1Dev

    img_path = os.path.join(repo_dir, 'Photos', FolderPhotos, NombreImagen)

    img = cv.imread(img_path)

    if img is None:
        print("No se pudo cargar la imagen:", img_path)
        raise FileNotFoundError(f"No se encontró la imagen en: {img_path}")


    return img

def ROI(img):
    # Seleccionar ROI manualmente
    # Arrastra con el mouse y presiona ENTER o SPACE para confirmar
    # Presiona C para cancelar
    roi = cv.selectROI("Select ROI", img, showCrosshair=True, fromCenter=False, printNotice=False)

    # # roi devuelve: (x, y, w, h)
    x, y, w, h = roi
    cv.destroyAllWindows()
    # print(f"Ancho: {w}, Alto: {h}") # Mostrar dimension
    return x, y, w, h

def croptoroi(img, x,y,w,h): #Crop y convierte a gris
    cropped = img[y:y+h, x:x+w]
    if cropped.size == 0:
        raise ValueError("El ROI salió vacío.")
    cropped = cv.cvtColor(cropped, cv.COLOR_BGR2GRAY)
    cropped = cropped.astype(np.float32) / 255.0
    return cropped

def basic_features(img):
    features = {}

    features["mean_intensity"] = float(np.mean(img))
    features["std_intensity"] = float(np.std(img))
    features["min_intensity"] = float(np.min(img))
    features["max_intensity"] = float(np.max(img))

    grad_x = cv.Sobel(img, cv.CV_32F, 1, 0, ksize=3)
    grad_y = cv.Sobel(img, cv.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    features["mean_grad"] = float(np.mean(grad_mag))
    features["std_grad"] = float(np.std(grad_mag))
    features["max_grad"] = float(np.max(grad_mag))

    lap = cv.Laplacian(img, cv.CV_32F)
    features["mean_abs_lap"] = float(np.mean(np.abs(lap)))
    features["std_lap"] = float(np.std(lap))

    return features




def main():
    fold = 'Polight' # Nombre de la carpeta donde está la foto
    imgname = 'PolarizedProG.jpeg'
    imgname2 = 'PolarizedProB.jpeg'
    img = cargarimagen(fold,imgname)
    img2 = cargarimagen(fold,imgname2)
    x, y, w, h = ROI(img)
    im1mat = croptoroi(img,x,y,w,h)
    im2mat = croptoroi(img2,x,y,w,h)
    features = basic_features(im1mat)
    for k, v in features.items():
        print(f"{k}: {v}")



main()