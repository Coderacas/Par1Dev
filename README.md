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

## V6

La version V6 consolida el prototipo como un sistema integrado de inspeccion,
clasificacion, calibracion visual y correccion mecanica. Los archivos centrales
de esta etapa estan en:

```text
PythonDev/Project/PrototypeDev/main.py
PythonDev/Project/PrototypeDev/calibrar_motores_luces.py
PythonDev/Project/PrototypeDev/motor_calibration.py
ArduinoControl/ArduinoFinalIntegration/FinalIntegration/FinalIntegration.ino
ML Model/train_model.py
```

### Clasificacion con machine learning

- `main.py` ya no depende del clasificador aleatorio.
- El modelo entrenado se carga desde `golf_ball_rf_model.pkl`.
- La funcion `clasificar()` usa el modelo con `predict_proba` cuando esta disponible.
- El umbral de probabilidad para pelota buena se guarda junto con el modelo.
- La memoria de estado conserva una pelota como `MALA` si alguna estacion previa o actual la marco como mala.
- El dataset principal de entrenamiento se encuentra en:

```text
PythonDev/Project/PrototypeDev/data/features_dataset_ml.csv
```

Para entrenar el modelo:

```powershell
python "ML Model\train_model.py"
```

El entrenamiento genera/actualiza el bundle del modelo, que despues consume
`main.py`.

### Captura de features

El sistema sigue usando 4 estaciones y 4 luces por estacion:

```text
NUM_ESTACIONES = 4
LUCES_POR_EST = 4
```

Cada estacion usa su ROI definido en `ROIS_POR_ESTACION` dentro de `main.py`.
Los scripts que capturan features o calibran usan esos ROIs como referencia
central para evitar desalineacion entre inspeccion y calibracion.

Las features por ROI incluyen:

- intensidad media, desviacion, minimo y maximo
- gradiente medio, desviacion y maximo
- laplaciano absoluto medio y desviacion
- porcentaje de glare

Por estacion se derivan estadisticas sobre las 4 luces:

```text
std, mean, max, min
```

### Orden fisico de luces

En V6 se corrigio el mapeo fisico de luces. El Arduino envia los pasos `1..16`,
pero el orden fisico real no empieza en la estacion 1:

```text
pasos  1-4  -> estacion 4
pasos  5-8  -> estacion 3
pasos  9-12 -> estacion 2
pasos 13-16 -> estacion 1
```

La funcion `decodificar_paso()` en `main.py` ya toma esto en cuenta. Por eso,
cualquier script que importe esa funcion queda alineado con el orden real de
las luces.

### Calibracion visual de motores

Se agrego una calibracion independiente en:

```text
PythonDev/Project/PrototypeDev/calibrar_motores_luces.py
```

Uso manual:

```powershell
python PythonDev\Project\PrototypeDev\calibrar_motores_luces.py
```

Dentro del script:

```text
calibrar
```

El script:

- prende las luces usando el Arduino
- captura L1-L4 por cada estacion
- superpone las 4 fotos de cada estacion con 25% cada una
- simula una iluminacion con las 4 luces encendidas
- detecta la geometria de la pelota dentro del ROI
- calcula el error visual respecto al centro del ROI
- dibuja los ROIs y la linea de error para revision manual
- manda correcciones al Arduino con comandos `R motor steps`

El comando de correccion serial tiene la forma:

```text
R 1 -120
R 2 80
R 3 150
R 4 -200
```

El Arduino responde con:

```text
CORRECCION_LISTA M1 -120
```

### Reglas actuales de correccion

La calibracion no usa PID completo. Es una correccion proporcional discreta:

```text
error_px -> steps = abs(error_px) * steps_per_pixel
```

Con:

- umbral minimo por estacion
- minimo de pasos
- maximo de pasos
- signo configurable por motor
- eje configurable por estacion

Ejes actuales:

```text
E1 -> x
E2 -> x
E3 -> y
E4 -> x
```

Esto corresponde al movimiento real de los rieles.

### Calibracion automatica dentro de `main.py`

`main.py` ahora puede hacer una calibracion automatica cada cierto numero de
ciclos completos:

```text
AUTO_CALIBRATION_EVERY_CYCLES = 5
```

Flujo:

1. El sistema inspecciona normalmente.
2. Cuando Arduino reporta `STEPPERS_LISTOS`, Python rota la memoria.
3. Cada 5 ciclos se marca una calibracion pendiente.
4. En el siguiente `IN PLACE`, Python primero ejecuta calibracion visual.
5. Aplica correcciones con `R motor steps`.
6. Luego inicia la captura normal de esa misma pelota.

La calibracion automatica no despliega fotos y no debe mezclar datos con el
ciclo normal de inspeccion. Usa buffers separados para no contaminar las
matrices de features.

### Arduino V6

El Arduino integrado esta en:

```text
ArduinoControl/ArduinoFinalIntegration/FinalIntegration/FinalIntegration.ino
```

Funciones principales:

- control de luces con registros 74HC595
- handshake de captura con `g`, pasos `1..G`, `k` y `z`
- control de steppers con comando `s`
- correccion visual por comando `R motor steps`
- apagado de luces con `o`
- apagado/reset con `x`
- servo clasificador con comandos `b` y `m`

Comandos seriales relevantes:

```text
g              iniciar secuencia de luces/fotos
k              ACK de foto capturada
b              servo a buena
m              servo a mala
s              mover steppers
o              apagar luces/salidas sin centrar servo
x              apagado/reset seguro
R motor steps  correccion relativa de un motor
```

### Servo clasificador

El servo clasificador usa:

```text
SERVO_BUENA = 120
SERVO_MALA  = 60
```

Para evitar que el servo se quede pegado al ir hacia `MALA`, se agrego una
pre-carga:

```text
SERVO_PRE_MALA_KICK = SERVO_BUENA + 10
SERVO_PRE_MALA_KICK_MS = 90
```

Cuando el sistema manda `m`, el servo primero se mueve un poco mas hacia el
lado de buena y despues cae hacia mala. Esto ayuda a despegar la mecanica si
venia cargada.

### Estado de V6

V6 ya integra:

- clasificacion con modelo entrenado
- captura multi-luz por estacion
- memoria de pelota por estacion
- servo para separar buena/mala
- steppers controlados desde Arduino
- calibracion visual independiente
- calibracion automatica cada 5 ciclos
- correccion por pasos desde Python hacia Arduino

Pendientes probables:

- seguir afinando umbrales de correccion con mas pruebas fisicas
- aumentar el dataset de entrenamiento
- validar repetibilidad despues de muchas pelotas seguidas
- documentar valores finales de ROIs y ganancias de calibracion cuando queden congelados
