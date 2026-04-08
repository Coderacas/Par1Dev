import cv2 as cv
import os

script_dir = os.path.dirname(os.path.abspath(__file__))   # PythonDev/BasicGenerals
repo_dir = os.path.dirname(os.path.dirname(script_dir))   # Par1Dev

imname = 'ouchie.jpg'
folname = 'Photos'
fol2name = 'Stock Pics'
img_path = os.path.join(repo_dir, folname, fol2name, imname)

img = cv.imread(img_path)

if img is None:
    print(f'No se pudo cargar la imagen: {img_path}')
else:
    print('Imagen cargada correctamente')
    print(img.shape)

# Cargar imagen (puede ser tu frame capturado)
img = cv.imread(img_path)

# #frame = cv.imread(img_path)

# # Seleccionar ROI manualmente
# # Arrastra con el mouse y presiona ENTER o SPACE para confirmar
# # Presiona C para cancelar
roi = cv.selectROI("Select ROI", img, showCrosshair=True, fromCenter=False)

# # roi devuelve: (x, y, w, h)
x, y, w, h = roi

# # Recortar ROI haces un tipo CROP
roi_crop = img[y:y+h, x:x+w] # Opción A si la variable es img
# #cropped = frame[y:y+h, x:x+w] # Opción B si la variable es frameN

# # printeas
# cv.imshow("Original", img)
#cv.imshow("ROI Crop", cropped)

print(f"ROI seleccionada: x={x}, y={y}, w={w}, h={h}")


# # ------------------------------------------------------------------------------------
# # Segundo método.
# # Si el código ya calcula lo siguiente (dibuja el circulo)

# #cx, cy = 320, 240
# #r = 120
# #cv.circle(img, (cx, cy), r, (0,255,0), 2)

# # Entonces para calcular el ROI sería unicamente usar: 

# #mask = np.zeros(img.shape[:2], dtype=np.uint8)
# #cv.circle(mask, (cx, cy), r, 255, -1)
# #roi = cv.bitwise_and(img, img, mask=mask)

cv.waitKey(0)
cv.destroyAllWindows()