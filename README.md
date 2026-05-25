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

## V4

- Integracion inicial de camara y comunicacion serial con Arduino.
- Captura automatica de imagen a partir de comandos enviados por Arduino.
- Aplicacion de un ROI fijo para recortar la pelota antes de procesarla.
- Calculo de `basic_features` y `glare_stats` sobre la imagen recortada.
- Primer handshake Arduino-Python para confirmar captura y evitar avances repetidos.
- Base preparada para pasar de una captura simple a una secuencia automatizada de inspeccion.

## V5

La version V5 integra el flujo principal de inspeccion automatica en
`PythonDev/Project/PrototypeDev/main.py`. Esta version ya conecta la camara,
la extraccion de caracteristicas, la memoria de pelotas por estacion y el
handshake serial con Arduino.

### Flujo principal de `main.py`

- Python detecta automaticamente el puerto del Arduino usando `pyserial`.
- Se inicializa la camara, se configura a `640x480` y se hace warmup antes de inspeccionar.
- El sistema trabaja con 4 estaciones (`NUM_ESTACIONES = 4`) y 4 luces por estacion (`LUCES_POR_EST = 4`).
- Cada estacion tiene su propio ROI en `ROIS_POR_ESTACION`.
- Por cada luz, Python captura una imagen en gris, recorta el ROI de la estacion correspondiente y extrae features.
- Las features usadas actualmente son intensidad, gradiente, laplaciano y porcentaje de glare.
- Al terminar las 4 luces de una estacion, Python genera un vector derivado usando `std`, `mean`, `max` y `min`.
- La clasificacion todavia esta como placeholder aleatorio en `clasificar()`. Esta parte se reemplazara por el modelo entrenado.
- Python mantiene una memoria de 4 posiciones para saber que pelota esta en cada estacion.

### Handshake Arduino-Python

El flujo actual depende de mensajes seriales para que Arduino y Python no avancen fuera de sincronizacion:

1. Arduino detecta la pelota en posicion con el sensor y manda:

   ```text
   IN PLACE
   ```

2. Python recibe `IN PLACE`, reinicia el ciclo interno y manda:

   ```text
   g
   ```

   Esto le indica al Arduino que puede iniciar la secuencia de luces y fotos.

3. Arduino prende una luz y manda el paso actual:

   ```text
   1, 2, 3, ..., 9, A, B, C, D, E, F, G
   ```

   Estos 16 pasos representan 4 luces por cada una de las 4 estaciones:

   - `1` a `4`: estacion 1, ROI 1
   - `5` a `8`: estacion 2, ROI 2
   - `9` a `C`: estacion 3, ROI 3
   - `D` a `G`: estacion 4, ROI 4

4. Python captura la foto, recorta el ROI correcto, extrae features y responde:

   ```text
   k
   ```

   La `k` confirma que la foto ya fue tomada y que Arduino puede avanzar a la siguiente luz.

5. Cuando Arduino termina toda la secuencia de fotos, manda:

   ```text
   z
   ```

6. Python procesa la clasificacion final y revisa la pelota en la posicion 4, que es la que sale del sistema.

7. Python manda el comando del servo segun la clasificacion:

   ```text
   b
   ```

   para pelota buena, o:

   ```text
   m
   ```

   para pelota mala.

8. Python espera `SERVO_SETTLE_S = 0.5` segundos para dar tiempo al servo.

9. Python manda:

   ```text
   s
   ```

   para pedirle al Arduino que mueva los steppers.

10. Arduino debe responder:

    ```text
    STEPPERS_LISTOS
    ```

    Cuando Python recibe este mensaje, rota la memoria: la posicion 4 sale, la 3 pasa a 4, la 2 pasa a 3, la 1 pasa a 2 y entra una nueva posicion vacia en la estacion 1.

11. Si los steppers no responden dentro de `STEPPER_TIMEOUT_S = 30.0`, Python manda:

    ```text
    x
    ```

    como apagado de seguridad.

### Arduino actual

Ya existe codigo de Arduino para controlar correctamente steppers y luces en:

```text
ArduinoControl/FinalArduinoTotal/FinalArduinoTotal.ino
```

Este codigo controla:

- los registros 74HC595 para luces y seleccion de steppers
- la secuencia de luces
- el avance automatico de steppers
- apagado general con `x`
- apagado de steppers con `0`

### Pendientes para la siguiente version

La siguiente version sera la integracion total del sistema. Para llegar a esa version falta:

- conectar `main.py` con el modelo entrenado usando el dataset real
- entrenar usando los hyperparameters tuneados del modelo final
- reemplazar el placeholder aleatorio de `clasificar()` por una prediccion real
- agregar el control fisico del servo al codigo de Arduino
- probablemente agregar mas sensores al Arduino para confirmar posicion y seguridad mecanica
- crear un script dedicado para capturar datos de training desde el prototipo real
- guardar las capturas/features con etiqueta de pelota buena o mala para alimentar el dataset
