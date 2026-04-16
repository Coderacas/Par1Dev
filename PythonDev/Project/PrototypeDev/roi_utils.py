import cv2 as cv
import numpy as np

def ROI(img):
    roi = cv.selectROI("Select ROI", img, showCrosshair=True, fromCenter=False, printNotice=False)
    x, y, w, h = roi
    cv.destroyAllWindows()
    return x, y, w, h

def croptoroi(img, x, y, w, h):
    cropped = img[y:y+h, x:x+w]
    if cropped.size == 0:
        raise ValueError("El ROI salió vacío.")
    cropped = cv.cvtColor(cropped, cv.COLOR_BGR2GRAY)
    cropped = cropped.astype(np.float32) / 255.0
    return cropped