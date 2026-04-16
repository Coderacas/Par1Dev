import cv2 as cv
import numpy as np

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