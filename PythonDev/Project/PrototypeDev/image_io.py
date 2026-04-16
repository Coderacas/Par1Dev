import cv2 as cv
import os

def cargarimagen(folder_photos, nombre_imagen):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)
    pythondev_dir = os.path.dirname(project_dir)
    repo_dir = os.path.dirname(pythondev_dir)

    img_path = os.path.join(repo_dir, 'Photos', folder_photos, nombre_imagen)

    img = cv.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"No se encontró la imagen en: {img_path}")

    return img