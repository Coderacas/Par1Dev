import cv2 as cv
import os

base_path = os.path.dirname(__file__) #Importar la dirección de la carpeta
imname = 'ouchie.jpg'
img_path = os.path.join(base_path, 'Photos',imname) #Dirección base + Photos + nombre de la foto 

img = cv.imread(img_path)

cv.imshow('Og',img)

# Convertir a gris
# gray = cv.cvtColor(img,cv.COLOR_BGR2GRAY)
# cv.imshow('Gray',gray)

#Blur 
# blur = cv.GaussianBlur(img, (5,5), cv.BORDER_ISOLATED)
# cv.imshow('blur',blur)

# # Edge Cascade
canny = cv.Canny(img, 150, 175) #Original canny
# ecanny = cv.Canny(blur, 150, 175) #Canny con blur (menos edges)
# cv.imshow('Canny OG',canny)
# cv.imshow('Canny Blur',ecanny)

# Dilating the image
dilated = cv.dilate(canny, (3,3), iterations=1)
# cv.imshow('Canny (OG)',canny)
# cv.imshow('Dilated Canny (OG)',dilated)

# Eroding
# eroded = cv.erode(dilated, (3,3), iterations=1) # Inversa de dilating
# cv.imshow('Canny (OG)',canny)
# cv.imshow('Dilated Canny (OG)',dilated)
# cv.imshow('Eroded', eroded)

# Resize
# resized = cv.resize(img, (1180,720), interpolation=cv.INTER_CUBIC) #Inter_area para mas pequeña, linear o cubic para agrandar
# cv.imshow('Resized', resized)


# Croppiing 
#print(img.shape)
cropped = img[:round(img.shape[0]/2), round(img.shape[1]/2):]
cv.imshow("Chop", cropped)

cv.waitKey(0)
