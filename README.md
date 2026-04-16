# Golf Ball Inspection System

Este repositorio contiene el desarrollo de un sistema de inspección de pelotas de golf usando visión por computadora, control de iluminación y procesamiento de imágenes en Python.

El objetivo general del proyecto es construir un sistema capaz de distinguir entre pelotas en buen estado y pelotas defectuosas, utilizando imágenes capturadas bajo diferentes condiciones de iluminación.

## Estructura del repositorio

    .
    ├── README.md
    ├── Photos/
    │   ├── stock/
    │   ├── goodpickstry1/
    │   └── badpicstry1/
    ├── Python Dev/
    │   ├── basic generals/
    │   └── project/
    └── Light control/

## Descripción de carpetas

### `Photos`

Carpeta que contiene imágenes y videos usados en el desarrollo del proyecto.

#### Subcarpetas

- `stock`: imágenes obtenidas de internet para referencia o pruebas iniciales.
- `goodpickstry1`: imágenes del primer prototipo de pelotas consideradas buenas, incluyendo 4 iluminaciones y un video.
- `badpicstry1`: imágenes del primer prototipo de pelotas consideradas defectuosas, incluyendo 4 iluminaciones y un video.

### `Python Dev`

Carpeta destinada al desarrollo del software en Python.

#### Subcarpetas

- `basic generals`: funciones genéricas, pruebas base y códigos de referencia.
- `project`: módulos del proyecto más cercanos a una versión final. Actualmente incluye un prototipo de selección de ROI. Dentro se encuentran FinalFunction 

### `Light control`

Carpeta con códigos de Arduino para el control de iluminación del sistema.

Su propósito es gestionar la activación de distintas fuentes de luz y apoyar la captura de imágenes bajo diferentes condiciones lumínicas.

## Estado actual

Por el momento, el proyecto incluye:

- organización inicial de imágenes
- separación entre muestras buenas y defectuosas
- pruebas con múltiples condiciones de iluminación
- prototipo básico para selección de ROI
- desarrollo inicial del control de luces

## Objetivo a futuro

Más adelante se busca integrar:

- captura estandarizada de imágenes
- análisis fotométrico
- extracción de características
- clasificación automática con machine learning
- integración completa entre visión, iluminación y sistema mecánico

## Notas

Este repositorio funciona como base de desarrollo para prototipos y pruebas del sistema.  
La estructura y los módulos seguirán evolucionando conforme avance el proyecto.

## V2 
* Selector de ROI desde cámara y fotos descargadas con calibración manual.
* Photos de alta calidad tomadas por el prototipo 

## V3
- Se modularizó el procesamiento de imágenes en archivos separados (`image_io.py`, `roi_utils.py`, `features.py`, `glare.py` y `main.py`).
- Ya se puede cargar una imagen desde el repositorio, seleccionar una ROI manualmente y recortarla con una sola calibración.
- La función de recorte ahora convierte la ROI a escala de grises, la normaliza a rango `[0,1]` y la deja en `float32`.
- Se implementó extracción de features básicas de la ROI:
  - intensidad media, desviación estándar, mínimo y máximo
  - gradiente medio, desviación estándar y máximo
  - laplaciano absoluto medio y desviación estándar
- Se corrigió un error de normalización doble que estaba reduciendo incorrectamente la intensidad máxima.
- Se creó una primera versión de `glare.py` para estimar el porcentaje de glare dentro de una ROI usando umbral de intensidad.
- Se dejó la base lista para el siguiente paso: procesar varias imágenes, hacer stack y avanzar hacia photometric stereo.