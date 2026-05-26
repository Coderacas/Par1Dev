// =====================================================
// PINES 74HC595
// =====================================================
int dataPin  = 11;
int clockPin = 12;
int latchPin = 8;

// =====================================================
// SERVO
// =====================================================
#include <Servo.h>

const int pinServo = 9;
const int SERVO_CENTRO = 90;
const int SERVO_DELTA  = 30;
const int SERVO_BUENA  = SERVO_CENTRO + SERVO_DELTA;
const int SERVO_MALA   = SERVO_CENTRO - SERVO_DELTA;

Servo servoClasificador;

// =====================================================
// SENSOR IN PLACE
// =====================================================
const int pinInPlace = A5;

// Si usas resistencia externa pull-down:
//   sensor activo = HIGH
//
// Si usas INPUT_PULLUP:
//   sensor activo = LOW
//
// En este código está configurado para activo HIGH.
const bool SENSOR_ACTIVO = HIGH;

// =====================================================
// STEPPER
// =====================================================
#include <Stepper.h>

const int pasosPorVuelta = 2048;
const int pasos90Grados  = 1024;

// Pines de bobinas del stepper
Stepper motor(pasosPorVuelta, 6, 5, 3, 4);

// Para que cada movimiento de 90° sea aprox 1 segundo.
// Si pierde pasos, baja a 10 o 12.
int velocidadStepper = 10;

// =====================================================
// TIEMPOS
// =====================================================
const int delayDespuesShift     = 20;
const int delayAntesDriver      = 200;
const int delayDriverEstable    = 500;
const int delayDespuesMotor     = 100;
const int delayEntreSteppers    = 100;

// =====================================================
// ESTADOS DE REGISTROS
// =====================================================
byte estadoReg1 = B00000000;   // SR1 luces 1-8
byte estadoReg2 = B00000000;   // SR2 luces 9-16
byte estadoReg3 = B00000000;   // SR3 drivers

// =====================================================
// SECUENCIA DE LUCES
// =====================================================
int pasoLuzActual  = 1;
const int PASO_MIN = 1;
const int PASO_MAX = 16;

bool esperandoAck = false;

// =====================================================
// ESTADOS DEL CICLO
// =====================================================
bool esperandoInPlace = true;
bool cicloEnProceso   = false;
bool inPlaceAnterior  = false;

// =====================================================
// SETUP
// =====================================================
void setup()
{
  pinMode(dataPin,  OUTPUT);
  pinMode(clockPin, OUTPUT);
  pinMode(latchPin, OUTPUT);

  pinMode(pinInPlace, INPUT);

  // Si NO tienes resistencia externa en A5, usa INPUT_PULLUP:
  // pinMode(pinInPlace, INPUT_PULLUP);
  // y cambia:
  // const bool SENSOR_ACTIVO = LOW;

  pinMode(3, OUTPUT);
  pinMode(4, OUTPUT);
  pinMode(5, OUTPUT);
  pinMode(6, OUTPUT);

  digitalWrite(dataPin, LOW);
  digitalWrite(clockPin, LOW);
  digitalWrite(latchPin, LOW);

  Serial.begin(9600);

  servoClasificador.attach(pinServo);
  servoClasificador.write(SERVO_CENTRO);

  motor.setSpeed(velocidadStepper);

  apagarBobinasStepper();

  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  estadoReg3 = B00000000;

  actualizarSalidas();

  Serial.println("LISTO");
}

// =====================================================
// LOOP
// =====================================================
void loop()
{
  revisarSensorInPlace();
  leerComandosSerial();
}

// =====================================================
// REVISAR SENSOR A5
// =====================================================
void revisarSensorInPlace()
{
  if (!esperandoInPlace) return;
  if (cicloEnProceso) return;

  bool inPlaceActual = digitalRead(pinInPlace);

  // Detectar flanco: antes no estaba activo, ahora sí
  if (inPlaceActual == SENSOR_ACTIVO && inPlaceAnterior == false)
  {
    Serial.println("IN PLACE");

    esperandoInPlace = false;
    cicloEnProceso   = true;
  }

  inPlaceAnterior = (inPlaceActual == SENSOR_ACTIVO);
}

// =====================================================
// LEER COMANDOS SERIAL
// =====================================================
void leerComandosSerial()
{
  if (Serial.available() > 0)
  {
    char dato = Serial.read();

    delay(5);
    while (Serial.available() > 0) Serial.read();

    if (dato == '\r' || dato == '\n') return;

    if      (dato == 'g') { iniciarSecuenciaFotos(); }
    else if (dato == 'k') { ackFoto(); }
    else if (dato == 'b') { servoPos(true);  }
    else if (dato == 'm') { servoPos(false); }
    else if (dato == 's') { ejecutarSecuenciaSteppers90(); }
    else if (dato == 'x') { apagarTodoSeguro(); resetearCiclo(); Serial.println("APAGADO"); }
    else if (dato == 'p') { probarRegistro3(); }
  }
}

// =====================================================
// RESETEAR CICLO PARA VOLVER A ESPERAR IN PLACE
// =====================================================
void resetearCiclo()
{
  esperandoAck     = false;
  esperandoInPlace = true;
  cicloEnProceso   = false;

  // Espera a que el sensor A5 se libere para evitar doble disparo
  while (digitalRead(pinInPlace) == SENSOR_ACTIVO)
  {
    delay(10);
  }

  inPlaceAnterior = false;

  apagarTodoSeguro();

  Serial.println("LISTO");
}

// =====================================================
// INICIAR SECUENCIA DE FOTOS
// =====================================================
void iniciarSecuenciaFotos()
{
  if (!cicloEnProceso) return;

  pasoLuzActual = PASO_MIN;
  esperandoAck  = false;

  encenderLuzYnotificar();
}

// =====================================================
// ACK DE FOTO → AVANZAR LUZ
// =====================================================
void ackFoto()
{
  if (!esperandoAck) return;

  esperandoAck = false;
  pasoLuzActual++;

  if (pasoLuzActual > PASO_MAX)
  {
    apagarTodasLasLuces();
    Serial.println("z");
  }
  else
  {
    encenderLuzYnotificar();
  }
}

// =====================================================
// ENCENDER LUZ Y NOTIFICAR
// =====================================================
void encenderLuzYnotificar()
{
  // Mientras se toman fotos, SR3 apagado
  estadoReg3 = B00000000;

  int bitIdx = pasoLuzActual - 1;

  estadoReg1 = B00000000;
  estadoReg2 = B00000000;

  if (bitIdx <= 7)
  {
    estadoReg1 = (1 << bitIdx);
  }
  else
  {
    estadoReg2 = (1 << (bitIdx - 8));
  }

  actualizarSalidas();

  char notif;

  if (pasoLuzActual <= 9)
    notif = '0' + pasoLuzActual;
  else
    notif = 'A' + (pasoLuzActual - 10);

  Serial.write(notif);

  esperandoAck = true;
}

// =====================================================
// APAGAR SOLO LUCES
// =====================================================
void apagarTodasLasLuces()
{
  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  actualizarSalidas();
}

// =====================================================
// SERVO
// =====================================================
void servoPos(bool buena)
{
  int angulo = buena ? SERVO_BUENA : SERVO_MALA;
  angulo = constrain(angulo, SERVO_CENTRO - SERVO_DELTA, SERVO_CENTRO + SERVO_DELTA);

  servoClasificador.write(angulo);

  if (buena) Serial.println("SERVO_BUENA");
  else       Serial.println("SERVO_MALA");
}

// =====================================================
// STEPPERS
// =====================================================
void ejecutarSecuenciaSteppers90()
{
  if (!cicloEnProceso) return;

  while (Serial.available()) Serial.read();

  apagarBobinasStepper();

  // Apagar luces y drivers antes de iniciar
  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  estadoReg3 = B00000000;
  actualizarSalidas();

  delay(delayAntesDriver);

  // =====================================================
  // DRIVER 1: salida física 1 del SR3
  // =====================================================
  estadoReg3 = B00000001;
  actualizarSalidas();

  delay(delayDriverEstable);

  motor.step(pasos90Grados);

  delay(delayDespuesMotor);

  apagarBobinasStepper();

  estadoReg3 = B00000000;
  actualizarSalidas();

  delay(delayEntreSteppers);

  // =====================================================
  // DRIVER 2: salida física 2 del SR3
  // =====================================================
  estadoReg3 = B00000010;
  actualizarSalidas();

  delay(delayDriverEstable);

  motor.step(pasos90Grados);

  delay(delayDespuesMotor);

  apagarBobinasStepper();

  estadoReg3 = B00000000;
  actualizarSalidas();

  delay(delayEntreSteppers);

  // =====================================================
  // DRIVER 3: salida física 3 del SR3
  // =====================================================
  estadoReg3 = B00000100;
  actualizarSalidas();

  delay(delayDriverEstable);

  motor.step(pasos90Grados);

  delay(delayDespuesMotor);

  apagarBobinasStepper();

  estadoReg3 = B00000000;
  actualizarSalidas();

  delay(delayEntreSteppers);

  // =====================================================
  // DRIVER 4: salida física 4 del SR3
  // =====================================================
  estadoReg3 = B00001000;
  actualizarSalidas();

  delay(delayDriverEstable);

  motor.step(pasos90Grados);

  delay(delayDespuesMotor);

  apagarBobinasStepper();

  estadoReg3 = B00000000;
  actualizarSalidas();

  apagarTodoSeguro();

  Serial.println("STEPPERS_LISTOS");

  resetearCiclo();
}

// =====================================================
// PRUEBA REGISTRO 3
// p = prueba automática SR3 salida 1 a 8
// =====================================================
void probarRegistro3()
{
  apagarBobinasStepper();

  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  estadoReg3 = B00000000;
  actualizarSalidas();

  delay(500);

  for (int i = 0; i < 8; i++)
  {
    estadoReg3 = (1 << i);
    actualizarSalidas();

    Serial.print("SR3 LOG=");
    imprimirByteBinarioSinEnter(estadoReg3);
    Serial.print(" FIS=");
    imprimirByteBinario(invertirByte(estadoReg3));

    delay(1000);

    estadoReg3 = B00000000;
    actualizarSalidas();

    delay(300);
  }

  estadoReg3 = B00000000;
  actualizarSalidas();

  Serial.println("SR3_OK");
}

// =====================================================
// APAGAR BOBINAS STEPPER
// =====================================================
void apagarBobinasStepper()
{
  digitalWrite(3, LOW);
  digitalWrite(4, LOW);
  digitalWrite(5, LOW);
  digitalWrite(6, LOW);
}

// =====================================================
// APAGADO SEGURO TOTAL
// =====================================================
void apagarTodoSeguro()
{
  apagarBobinasStepper();
  servoClasificador.write(SERVO_CENTRO);

  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  estadoReg3 = B00000000;

  actualizarSalidas();

  digitalWrite(latchPin, LOW);
  digitalWrite(clockPin, LOW);
  digitalWrite(dataPin, LOW);
}

// =====================================================
// ACTUALIZAR SHIFT REGISTERS
// =====================================================
void actualizarSalidas()
{
  enviar24(estadoReg1, estadoReg2, estadoReg3);
  delay(delayDespuesShift);
}

// =====================================================
// ENVIAR 24 BITS
// =====================================================
// Cadena física:
// Arduino -> SR1 -> SR2 -> SR3
//
// Para que reg3 llegue al tercer chip,
// se manda primero reg3, luego reg2, luego reg1.
//
// Cada byte se invierte antes de mandarse:
// 00000001 -> 10000000
// 00000010 -> 01000000
// =====================================================
void enviar24(byte reg1, byte reg2, byte reg3)
{
  byte reg1Fisico = invertirByte(reg1);
  byte reg2Fisico = invertirByte(reg2);
  byte reg3Fisico = invertirByte(reg3);

  digitalWrite(latchPin, LOW);
  delayMicroseconds(5);

  shiftOut(dataPin, clockPin, LSBFIRST, reg3Fisico);  // SR3 drivers
  shiftOut(dataPin, clockPin, LSBFIRST, reg2Fisico);  // SR2 luces 9-16
  shiftOut(dataPin, clockPin, LSBFIRST, reg1Fisico);  // SR1 luces 1-8

  delayMicroseconds(5);

  digitalWrite(latchPin, HIGH);
  delayMicroseconds(20);
  digitalWrite(latchPin, LOW);

  digitalWrite(clockPin, LOW);
  digitalWrite(dataPin, LOW);
}

// =====================================================
// INVERTIR BYTE
// =====================================================
byte invertirByte(byte x)
{
  byte y = 0;

  for (int i = 0; i < 8; i++)
  {
    if (bitRead(x, i))
    {
      bitSet(y, 7 - i);
    }
  }

  return y;
}

// =====================================================
// DEBUG
// =====================================================
void imprimirByteBinario(byte valor)
{
  for (int i = 7; i >= 0; i--)
    Serial.print(bitRead(valor, i));

  Serial.println();
}

void imprimirByteBinarioSinEnter(byte valor)
{
  for (int i = 7; i >= 0; i--)
    Serial.print(bitRead(valor, i));
}
