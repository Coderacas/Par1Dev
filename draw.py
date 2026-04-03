import cv2 as cv 
import numpy as np

# img = (np.random.rand(300, 300,3) * 255).astype(np.uint8)

img = np.zeros((300,300,3), dtype='uint8')

#Paint an image
# img[200:,100:] = 0, 51, 0

# #Draw a rectangle
# cv.rectangle(img,(0,0), (100,200), (0,255,0), thickness=2)

# Draw a circle 
# cv.circle(img, (150,150), 50, (255,0,0), thickness=2)

# Draw a line 
# cv.line(img, (20,20), (150, 300), (0,255,0), thickness=5)

# Put text 
cv.putText(img,"Ball",(150,150), cv.FONT_HERSHEY_TRIPLEX,1,(255,0,0))

cv.imshow('Imagen',img)

while True:
    if cv.waitKey(1) & 0xFF==ord('q'):
        break

