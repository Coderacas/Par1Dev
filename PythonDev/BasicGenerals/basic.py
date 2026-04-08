import cv2 as cv
import os

script_dir = os.path.dirname(os.path.abspath(__file__))   # PythonDev/BasicGenerals
repo_dir = os.path.dirname(os.path.dirname(script_dir))   # Par1Dev

imname = 'ouchie.jpg'
img_path = os.path.join(repo_dir, 'Photos', 'Stock Pics', imname)

img = cv.imread(img_path)

if img is None:
    print(f'No se pudo cargar la imagen: {img_path}')
else:
    print('Imagen cargada correctamente')
    print(img.shape)

img = cv.imread(img_path)

cv.imshow('Og',img)

# Convertir a gris
gray = cv.cvtColor(img,cv.COLOR_BGR2GRAY)
cv.imshow('Gray',gray)

#Blur 
blur = cv.GaussianBlur(img, (5,5), cv.BORDER_ISOLATED)
cv.imshow('blur',blur)

# # Edge Cascade
canny = cv.Canny(img, 150, 175) #Original canny
ecanny = cv.Canny(blur, 150, 175) #Canny con blur (menos edges)
cv.imshow('Canny OG',canny)
cv.imshow('Canny Blur',ecanny)

# Dilating the image
dilated = cv.dilate(canny, (3,3), iterations=1)
cv.imshow('Canny (OG)',canny)
cv.imshow('Dilated Canny (OG)',dilated)

# Eroding
eroded = cv.erode(dilated, (3,3), iterations=1) # Inversa de dilating
#cv.imshow('Canny (OG)',canny)
cv.imshow('Dilated Canny (OG)',dilated)
cv.imshow('Eroded', eroded)

# Resize
resized = cv.resize(img, (1180,720), interpolation=cv.INTER_CUBIC) #Inter_area para mas pequeña, linear o cubic para agrandar
cv.imshow('Resized', resized)


# Croppiing 
#print(img.shape)
cropped = img[:round(img.shape[0]/2), round(img.shape[1]/2):]
cv.imshow("Chop", cropped)

cv.waitKey(0)
