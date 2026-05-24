#include <Stepper.h>

// =====================================================
// PINES 74HC595
// =====================================================
int dataPin = 11;     // DATA / DS / SER
int clockPin = 12;    // CLOCK / SH_CP / SRCLK
int latchPin = 8;     // LATCH / ST_CP / RCLK

// =====================================================
// STEPPER
// =====================================================
const int stepsPerRevolution = 2048;
const int steps90Degrees = stepsPerRevolution / 4;

// Pines de señal del stepper
// IMPORTANTE: no usar 8, 11 ni 12 porque ya son del 74HC595
Stepper myStepper(stepsPerRevolution, 3, 5, 4, 6);

// =====================================================
// SECUENCIA DE LUCES
// Registro 1 = luces 1 a 8
// Registro 2 = luces 9 a 16
// Registro 3 = selección de steppers
// =====================================================

byte secuenciaLucesReg1[] = {
  B00000001,   // a: luz 1
  B00000010,   // b: luz 2
  B00000100,   // c: luz 3
  B00001000,   // d: luz 4
  B00010000,   // e: luz 5
  B00000000    // f: apagado
};

byte secuenciaLucesReg2[] = {
  B00000000,   // a
  B00000000,   // b
  B00000000,   // c
  B00000000,   // d
  B00000001,   // e: luz 9
  B00000000    // f: apagado
};

char mensajesLuces[] = {
  'a',
  'b',
  'c',
  'd',
  'e',
  'f'
};

int pasoLuzActual = 0;
int totalPasosLuces = 6;
bool secuenciaLucesActiva = false;

// =====================================================
// SECUENCIA DE STEPPERS
// Registro 3
// =====================================================

byte seleccionStepper[] = {
  B00000001,   // stepper 1
  B00000010,   // stepper 2
  B00000100,   // stepper 3
  B00001000,   // stepper 4
  B00010000    // stepper 5
};

int totalSteppers = 5;

// =====================================================
// ESTADOS ACTUALES DE LOS 3 REGISTROS
// =====================================================

byte estadoReg1 = B00000000;   // luces 1-8
byte estadoReg2 = B00000000;   // luces 9-16
byte estadoReg3 = B00000000;   // steppers

// =====================================================
// SETUP
// =====================================================

void setup()
{
  pinMode(dataPin, OUTPUT);
  pinMode(clockPin, OUTPUT);
  pinMode(latchPin, OUTPUT);

  Serial.begin(9600);

  myStepper.setSpeed(10);

  apagarTodo();

  Serial.println("Sistema listo.");
  Serial.println("Comandos:");
  Serial.println("k = iniciar / avanzar secuencia de luces");
  Serial.println("a = ejecutar secuencia automatica de steppers");
  Serial.println("0 = apagar steppers");
  Serial.println("x = apagar todo");
}

// =====================================================
// LOOP PRINCIPAL
// =====================================================

void loop()
{
  if (Serial.available() > 0)
  {
    char dato = Serial.read();

    if (dato == 'k')
    {
      controlarSecuenciaLuces();
    }

    else if (dato == 'a')
    {
      ejecutarSecuenciaSteppers();
    }

    else if (dato == '0')
    {
      apagarSteppers();
    }

    else if (dato == 'x')
    {
      apagarTodo();
      secuenciaLucesActiva = false;
      pasoLuzActual = 0;
      Serial.println("Todo apagado.");
    }
  }
}

// =====================================================
// CONTROL DE LUCES CON k
// =====================================================

void controlarSecuenciaLuces()
{
  if (secuenciaLucesActiva == false)
  {
    secuenciaLucesActiva = true;
    pasoLuzActual = 0;

    Serial.println("Iniciando secuencia de luces...");
  }

  ejecutarPasoLuz();

  pasoLuzActual++;

  if (pasoLuzActual >= totalPasosLuces)
  {
    pasoLuzActual = 0;
    secuenciaLucesActiva = false;

    Serial.println("Secuencia de luces terminada.");
  }
}

void ejecutarPasoLuz()
{
  estadoReg1 = secuenciaLucesReg1[pasoLuzActual];
  estadoReg2 = secuenciaLucesReg2[pasoLuzActual];

  // No se toca estadoReg3 para no afectar steppers
  actualizarSalidas();

  delay(25);   // Tiempo para estabilizar iluminación / tomar foto

  Serial.println(mensajesLuces[pasoLuzActual]);
}

// =====================================================
// CONTROL AUTOMATICO DE STEPPERS CON a
// =====================================================

void ejecutarSecuenciaSteppers()
{
  Serial.println("Iniciando secuencia automatica de steppers...");

  for (int i = 0; i < totalSteppers; i++)
  {
    Serial.print("Moviendo stepper ");
    Serial.println(i + 1);

    estadoReg3 = seleccionStepper[i];
    actualizarSalidas();

    delay(50);   // Tiempo para habilitar el driver/motor

    myStepper.step(steps90Degrees);

    estadoReg3 = B00000000;
    actualizarSalidas();

    delay(1000);
  }

  Serial.println("Secuencia de steppers terminada.");
}

void apagarSteppers()
{
  estadoReg3 = B00000000;
  actualizarSalidas();

  Serial.println("Steppers apagados.");
}

// =====================================================
// CONTROL GENERAL DE REGISTROS
// =====================================================

void apagarTodo()
{
  estadoReg1 = B00000000;
  estadoReg2 = B00000000;
  estadoReg3 = B00000000;

  actualizarSalidas();
}

void actualizarSalidas()
{
  enviar24(estadoReg1, estadoReg2, estadoReg3);
}

void enviar24(byte registro1, byte registro2, byte registro3)
{
  digitalWrite(latchPin, LOW);

  // En una cadena de 3 registros:
  // primero se manda el registro mas lejano
  // ultimo se manda el registro mas cercano al Arduino

  shiftOut(dataPin, clockPin, MSBFIRST, registro3);  // steppers
  shiftOut(dataPin, clockPin, MSBFIRST, registro2);  // luces 9-16
  shiftOut(dataPin, clockPin, MSBFIRST, registro1);  // luces 1-8

  digitalWrite(latchPin, HIGH);
}
