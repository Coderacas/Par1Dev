#include <Stepper.h>

// Pines del 74HC595
int dataPin = 5;    // DS
int latchPin = 6;   // ST_CP / RCLK
int clockPin = 7;   // SH_CP / SRCLK

// Stepper
const int stepsPerRevolution = 2048;
const int steps90Degrees = stepsPerRevolution / 4;

// Pines que mandan la señal al stepper
Stepper myStepper(stepsPerRevolution, 8, 10, 9, 11);

// Salidas del shift register para seleccionar cada stepper
byte seleccionStepper[] = {
  B00000001,
  B00000010,
  B00000100,
  B00001000,
  B00010000
};

int totalSteppers = 5;
bool secuenciaActiva = false;

void setup() {
  pinMode(dataPin, OUTPUT);
  pinMode(clockPin, OUTPUT);
  pinMode(latchPin, OUTPUT);

  Serial.begin(9600);

  myStepper.setSpeed(10);

  apagarShiftRegister();

  Serial.println("Listo. Envia 's' por Serial para iniciar la secuencia.");
}

void loop() {
  if (Serial.available() > 0) {
    char dato = Serial.read();

    if (dato == 's' && secuenciaActiva == false) {
      secuenciaActiva = true;

      Serial.println("Iniciando secuencia...");
      ejecutarSecuenciaSteppers();

      secuenciaActiva = false;
      Serial.println("Secuencia terminada.");
    }
  }
}

void ejecutarSecuenciaSteppers() {
  for (int i = 0; i < totalSteppers; i++) {
    Serial.print("Activando stepper ");
    Serial.println(i + 1);

    enviarShiftRegister(seleccionStepper[i]);

    delay(50);

    moverStepper90();

    apagarShiftRegister();

    delay(1000);
  }
}

void moverStepper90() {
  myStepper.step(steps90Degrees);
}

void enviarShiftRegister(byte dato) {
  digitalWrite(latchPin, LOW);
  shiftOut(dataPin, clockPin, MSBFIRST, dato);
  digitalWrite(latchPin, HIGH);
}

void apagarShiftRegister() {
  enviarShiftRegister(B00000000);
}
