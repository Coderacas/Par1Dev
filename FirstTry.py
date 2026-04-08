import cv2 as cv
import os

base_path = os.path.dirname(__file__) #Importar la dirección de la carpeta
imname = 'RealPic.jpg'
img_path = os.path.join(base_path, 'Photos',imname) #Dirección base + Photos + nombre de la foto 

img = cv.imread(img_path)

# Resize
resized = cv.resize(img, (1280,720), interpolation=cv.INTER_CUBIC) #Inter_area para mas pequeña, linear o cubic para agrandar

height = resized.shape[0]
width = resized.shape[1]
# Draw a circle 
cv.circle(resized, (int(width/2),height//2), 50, (255,0,0), thickness=2)

cv.imshow('Resized', resized)

cv.waitKey(0)

