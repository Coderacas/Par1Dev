#Este código ya utiliza una imagen caputrada para tomar dos ROIs con una sola calibración

import cv2 as cv
import os

def cargarimagen(FolderPhotos,NombreImagen):
    current_dir = os.path.dirname(os.path.abspath(__file__))   # .../PythonDev/Project/PrototypeDev
    project_dir = os.path.dirname(current_dir)                 # .../PythonDev/Project
    pythondev_dir = os.path.dirname(project_dir)               # .../PythonDev
    repo_dir = os.path.dirname(pythondev_dir)                  # .../Par1Dev

    img_path = os.path.join(repo_dir, 'Photos', FolderPhotos, NombreImagen)

    print("Ruta:", img_path)
    print("Existe:", os.path.exists(img_path))

    img = cv.imread(img_path)

    if img is None:
        print("No se pudo cargar la imagen:", img_path)
        raise FileNotFoundError(f"No se encontró la imagen en: {img_path}")

    print("Imagen cargada correctamente")

    # Cargar imagen (puede ser tu frame capturado)
    img = cv.imread(img_path)

    return img

def ROI(img):
    # Seleccionar ROI manualmente
    # Arrastra con el mouse y presiona ENTER o SPACE para confirmar
    # Presiona C para cancelar
    roi = cv.selectROI("Select ROI", img, showCrosshair=True, fromCenter=False)

    # # roi devuelve: (x, y, w, h)
    x, y, w, h = roi
    cv.destroyAllWindows()
    return x, y, w, h

def croptoroi(img, x,y,w,h):
    cropped = img[y:y+h, x:x+w] 
    cv.imshow("ROI Crop", cropped)
    cv.waitKey(0)
    cv.destroyAllWindows()



   
# # Segundo método.
# # # Si el código ya calcula lo siguiente (dibuja el circulo)
# #cx, cy = 320, 240
# # #r = 120
# #cv.circle(img, (cx, cy), r, (0,255,0), 2)

# # Entonces para calcular el ROI sería unicamente usar: 

# #mask = np.zeros(img.shape[:2], dtype=np.uint8)
# #cv.circle(mask, (cx, cy), r, 255, -1)
# #roi = cv.bitwise_and(img, img, mask=mask)


def main():
    fold = 'Polight' # Nombre de la carpeta donde está la foto
    imgname = 'PolarizedProG.jpeg'
    imgname2 = 'PolarizedProB.jpeg'
    img = cargarimagen(fold,imgname)
    img2 = cargarimagen(fold,imgname2)
    x, y, w, h = ROI(img)
    croptoroi(img,x,y,w,h)
    croptoroi(img2,x,y,w,h)



main()