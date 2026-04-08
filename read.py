import cv2 as cv
import os

base_path = os.path.dirname(__file__) #Importar la dirección de la carpeta
imname = 'RealPic.jpg'
img_path = os.path.join(base_path, 'Photos',imname) #Dirección base + Photos + nombre de la foto 

img = cv.imread(img_path)

cv.imshow('RealOg',img)

while True:
    if cv.waitKey(1) & 0xFF==ord('q'):
        break
