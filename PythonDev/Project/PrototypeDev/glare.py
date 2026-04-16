import numpy as np

def glare_mask(img_gray_float, bright_thr=0.98):
    """
    img_gray_float: imagen 2D en escala de grises, tipo float32, rango [0, 1]
    bright_thr: umbral para considerar un pixel como glare
    """
    mask = img_gray_float >= bright_thr
    return mask

def glare_percentage(img_gray_float, bright_thr=0.98):
    """
    Regresa el porcentaje de pixeles con glare dentro del ROI.
    """
    mask = glare_mask(img_gray_float, bright_thr=bright_thr)
    percentage = float(np.mean(mask) * 100.0)
    return percentage

def glare_stats(img_gray_float, bright_thr=0.98):
    """
    Regresa métricas básicas de glare.
    """
    mask = glare_mask(img_gray_float, bright_thr=bright_thr)

    glare_pixels = int(np.sum(mask))
    total_pixels = int(mask.size)
    percentage = float((glare_pixels / total_pixels) * 100.0)
    max_intensity = float(np.max(img_gray_float))

    return {
        "glare_pixels": glare_pixels,
        "total_pixels": total_pixels,
        "glare_percentage": percentage,
        "max_intensity": max_intensity,
        "threshold": bright_thr
    }