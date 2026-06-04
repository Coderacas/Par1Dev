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
int servoAnguloActual = SERVO_BUENA;

// =====================================================
// SENSOR IN PLACE
// =====================================================
const int pinInPlace = A0;

// Si usas resistencia externa pull-down:
//   sensor activo = HIGH
//
// Si usas INPUT_PULLUP:
//   sensor activo = LOW
//
// En este codigo esta configurado para activo HIGH.
const bool SENSOR_ACTIVO = HIGH;

// =====================================================
// STEPPER
// =====================================================
#include <Stepper.h>

const int pasosPorVuelta = 2048;
const int pasos90Grados  = pasosPorVuelta / 4;
const int pasos180Grados = pasosPorVuelta / 2;

// Pines de bobinas del stepper
const int phasePins[4] = {6, 5, 3, 4};

// Un objeto por motor permite cambiar el orden de fases sin recablear.
// Todos usan los mismos pines fisicos; SR3 selecciona que ULN2003 queda activo.
Stepper motor1(pasosPorVuelta, phasePins[0], phasePins[1], phasePins[2], phasePins[3]);
Stepper motor2(pasosPorVuelta, phasePins[0], phasePins[1], phasePins[2], phasePins[3]);
Stepper motor3(pasosPorVuelta, phasePins[0], phasePins[1], phasePins[2], phasePins[3]);
Stepper motor4(pasosPorVuelta, phasePins[0], phasePins[1], phasePins[2], phasePins[3]);

// Si no termina el giro o pierde pasos con carga, baja la velocidad.
int velocidadStepper = 5;

// Cada motor comparte los mismos pines de fase y se selecciona con SR3.
const byte seleccionStepper[4] = {
  B00000001,  // M1
  B00000010,  // M2
  B00000100,  // M3
  B00001000   // M4 - referencia
};

int steps180PorMotor[4] = {
  1024,            // M1
  1024,  // M2
  1024,  // M3
  1024             // M4
};

int direccionPorMotor[4] = {
  1,   // M1
  -1,   // M2
  1,   // M3
  1    // M4
};

const int stepsPruebaCalibracion[4] = {512, 1024, 2048, 4096};
const int delayFaseLenta = 400;
const int ciclosFaseLenta = 2;

// Variantes para diagnosticar orden de fases.
// Los valores son indices dentro de phasePins: 0=IN1, 1=IN2, 2=IN3, 3=IN4.
const byte ordenesFase[4][4] = {
  {0, 1, 2, 3},  // IN1, IN2, IN3, IN4
  {0, 2, 1, 3},  // IN1, IN3, IN2, IN4
  {0, 1, 3, 2},  // IN1, IN2, IN4, IN3
  {3, 2, 1, 0}   // IN4, IN3, IN2, IN1
};

const byte ordenFasePorMotor[4] = {
  0,  // M1
  0,  // M2
  0,  // M3
  0   // M4 referencia
};

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
// PROTOTIPOS
// =====================================================
void moverStepperSeleccionado(int indiceMotor, int steps);
void apagarTodoSeguro(bool centrarServo);
void ejecutarCorreccionSerial();

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
  servoClasificador.write(servoAnguloActual);

  motor1.setSpeed(velocidadStepper);
  motor2.setSpeed(velocidadStepper);
  motor3.setSpeed(velocidadStepper);
  motor4.setSpeed(velocidadStepper);

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
// REVISAR SENSOR A0
// =====================================================
void revisarSensorInPlace()
{
  if (!esperandoInPlace) return;
  if (cicloEnProceso) return;

  bool inPlaceActual = digitalRead(pinInPlace);

  // Detectar flanco: antes no estaba activo, ahora si
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

    if (dato == 'R')
    {
      ejecutarCorreccionSerial();
      return;
    }

    delay(5);
    while (Serial.available() > 0) Serial.read();

    if (dato == '\r' || dato == '\n') return;

    if      (dato == 'g') { iniciarSecuenciaFotos(); }
    else if (dato == 'k') { ackFoto(); }
    else if (dato == 'b') { servoPos(true);  }
    else if (dato == 'm') { servoPos(false); }
    else if (dato == 's') { ejecutarSecuenciaSteppers180(); }
    else if (dato == 'o') { apagarTodoSeguro(false); Serial.println("LUCES_APAGADAS"); }
    else if (dato == 'x') { apagarTodoSeguro(true); resetearCiclo(); Serial.println("APAGADO"); }
    else if (dato == 'p') { probarRegistro3(); }
    else if (dato == 'f') { probarFasesLentasTodos(); }
    else if (dato == 'c') { probarCalibracionStepsTodos(); }
    else if (dato == 'v') { probarVariantesFaseTodos(); }
    else if (dato == '1') { moverStepperDiagnostico(0); }
    else if (dato == '2') { moverStepperDiagnostico(1); }
    else if (dato == '3') { moverStepperDiagnostico(2); }
    else if (dato == '4') { moverStepperDiagnostico(3); }
  }
}

// =====================================================
// CORRECCION VISUAL POR PYTHON
// Comando:
//   R motor steps
// Ejemplo:
//   R 1 -12
// motor: 1..4
// steps: pasos relativos, puede ser negativo
// =====================================================
void ejecutarCorreccionSerial()
{
  int motor = Serial.parseInt();
  int steps = Serial.parseInt();

  while (Serial.available() > 0) Serial.read();

  if (motor < 1 || motor > 4 || steps == 0)
  {
    Serial.println("CORRECCION_INVALIDA");
    return;
  }

  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  estadoReg3 = B00000000;
  actualizarSalidas();

  moverStepperSeleccionado(motor - 1, steps);

  apagarTodoSeguro(false);

  Serial.print("CORRECCION_LISTA M");
  Serial.print(motor);
  Serial.print(" ");
  Serial.println(steps);
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

  apagarTodoSeguro(false);

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
// ACK DE FOTO -> AVANZAR LUZ
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

  servoClasificador.write(angulo);
  servoAnguloActual = angulo;
}

// =====================================================
// STEPPERS
// =====================================================
void ejecutarSecuenciaSteppers180()
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

  for (int i = 0; i < 4; i++)
  {
    moverStepperSeleccionado(i, steps180PorMotor[i]);

    if (i < 3)
    {
      delay(delayEntreSteppers);
    }
  }

  apagarTodoSeguro(false);

  Serial.println("STEPPERS_LISTOS");

  resetearCiclo();
}

// =====================================================
// MOVER UN STEPPER SELECCIONADO POR SR3
// =====================================================
void moverStepperSeleccionado(int indiceMotor, int steps)
{
  if (indiceMotor < 0 || indiceMotor >= 4) return;

  apagarBobinasStepper();

  estadoReg3 = seleccionStepper[indiceMotor];
  actualizarSalidas();

  delay(delayDriverEstable);

  setSpeedMotor(indiceMotor, velocidadStepper);
  stepMotor(indiceMotor, steps * direccionPorMotor[indiceMotor]);

  delay(delayDespuesMotor);

  apagarBobinasStepper();

  estadoReg3 = B00000000;
  actualizarSalidas();
}

void setSpeedMotor(int indiceMotor, int velocidad)
{
  if      (indiceMotor == 0) motor1.setSpeed(velocidad);
  else if (indiceMotor == 1) motor2.setSpeed(velocidad);
  else if (indiceMotor == 2) motor3.setSpeed(velocidad);
  else if (indiceMotor == 3) motor4.setSpeed(velocidad);
}

void stepMotor(int indiceMotor, int steps)
{
  if      (indiceMotor == 0) motor1.step(steps);
  else if (indiceMotor == 1) motor2.step(steps);
  else if (indiceMotor == 2) motor3.step(steps);
  else if (indiceMotor == 3) motor4.step(steps);
}

// =====================================================
// TEST INDIVIDUAL DE 180 GRADOS CALIBRADOS
// 1,2,3,4 = mueve solo ese motor con steps180PorMotor[]
// =====================================================
void moverStepperDiagnostico(int indiceMotor)
{
  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  estadoReg3 = B00000000;
  actualizarSalidas();

  moverStepperSeleccionado(indiceMotor, steps180PorMotor[indiceMotor]);

  apagarTodoSeguro(false);
  Serial.println("TEST_MOTOR_LISTO");
}

// =====================================================
// TEST LENTO DE FASES / LEDS ULN2003
// f = prueba M1, M2, M3, M4 con 400 ms por fase
// Secuencia: IN1, IN1+IN2, IN2, IN2+IN3, ...
// =====================================================
void probarFasesLentasTodos()
{
  estadoReg1 = B00000000;
  estadoReg2 = B00000000;

  for (int i = 0; i < 4; i++)
  {
    probarFasesLentasMotor(i);
    delay(1000);
  }

  apagarTodoSeguro(false);
  Serial.println("FASES_LENTAS_LISTAS");
}

void probarFasesLentasMotor(int indiceMotor)
{
  const byte fases[8][4] = {
    {HIGH, LOW,  LOW,  LOW },
    {HIGH, HIGH, LOW,  LOW },
    {LOW,  HIGH, LOW,  LOW },
    {LOW,  HIGH, HIGH, LOW },
    {LOW,  LOW,  HIGH, LOW },
    {LOW,  LOW,  HIGH, HIGH},
    {LOW,  LOW,  LOW,  HIGH},
    {HIGH, LOW,  LOW,  HIGH}
  };

  apagarBobinasStepper();

  estadoReg3 = seleccionStepper[indiceMotor];
  actualizarSalidas();

  Serial.print("FASES_M");
  Serial.println(indiceMotor + 1);

  delay(delayDriverEstable);

  for (int ciclo = 0; ciclo < ciclosFaseLenta; ciclo++)
  {
    for (int fase = 0; fase < 8; fase++)
    {
      Serial.print("M");
      Serial.print(indiceMotor + 1);
      Serial.print(" FASE ");
      Serial.println(fase + 1);

      escribirFase(fases[fase], ordenFasePorMotor[indiceMotor]);

      delay(delayFaseLenta);
    }
  }

  apagarBobinasStepper();

  estadoReg3 = B00000000;
  actualizarSalidas();
}

void escribirFase(const byte fase[4], byte ordenIdx)
{
  if (ordenIdx >= 4) ordenIdx = 0;

  for (int pin = 0; pin < 4; pin++)
  {
    digitalWrite(phasePins[pin], LOW);
  }

  for (int faseIdx = 0; faseIdx < 4; faseIdx++)
  {
    digitalWrite(phasePins[ordenesFase[ordenIdx][faseIdx]], fase[faseIdx]);
  }
}

// =====================================================
// TEST DE VARIANTES DE ORDEN DE FASE
// v = prueba cada motor con los 4 ordenes definidos arriba
// =====================================================
void probarVariantesFaseTodos()
{
  const byte fases[8][4] = {
    {HIGH, LOW,  LOW,  LOW },
    {HIGH, HIGH, LOW,  LOW },
    {LOW,  HIGH, LOW,  LOW },
    {LOW,  HIGH, HIGH, LOW },
    {LOW,  LOW,  HIGH, LOW },
    {LOW,  LOW,  HIGH, HIGH},
    {LOW,  LOW,  LOW,  HIGH},
    {HIGH, LOW,  LOW,  HIGH}
  };

  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  actualizarSalidas();

  for (int motorIdx = 0; motorIdx < 4; motorIdx++)
  {
    for (int ordenIdx = 0; ordenIdx < 4; ordenIdx++)
    {
      apagarBobinasStepper();

      estadoReg3 = seleccionStepper[motorIdx];
      actualizarSalidas();

      Serial.print("M");
      Serial.print(motorIdx + 1);
      Serial.print(" ORDEN_FASE_");
      Serial.println(ordenIdx + 1);

      delay(delayDriverEstable);

      for (int fase = 0; fase < 8; fase++)
      {
        escribirFase(fases[fase], ordenIdx);
        delay(delayFaseLenta);
      }

      apagarBobinasStepper();
      estadoReg3 = B00000000;
      actualizarSalidas();
      delay(1000);
    }
  }

  apagarTodoSeguro(false);
  Serial.println("VARIANTES_FASE_LISTAS");
}

// =====================================================
// TEST DE STEPS POR MOTOR
// c = M1..M4 con 512, 1024, 2048, 4096 steps
// Registrar fisicamente cuanto gira cada motor.
// =====================================================
void probarCalibracionStepsTodos()
{
  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  actualizarSalidas();

  for (int motorIdx = 0; motorIdx < 4; motorIdx++)
  {
    for (int pruebaIdx = 0; pruebaIdx < 4; pruebaIdx++)
    {
      moverStepperSeleccionado(motorIdx, stepsPruebaCalibracion[pruebaIdx]);
      delay(1500);
    }
  }

  apagarTodoSeguro(false);
  Serial.println("CALIBRACION_STEPS_LISTA");
}

// =====================================================
// PRUEBA REGISTRO 3
// p = prueba automatica SR3 salida 1 a 8
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
void apagarTodoSeguro(bool centrarServo = false)
{
  apagarBobinasStepper();

  if (centrarServo)
  {
    servoClasificador.write(SERVO_CENTRO);
    servoAnguloActual = SERVO_CENTRO;
  }

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
// Cadena fisica:
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
