#include <Stepper.h>

const int stepsPerRevolution = 2048;
const int LED = 7;
const int triggerPin = 2;

Stepper motor(stepsPerRevolution, 8, 10, 9, 11);

bool esperandoRespuesta = false;
bool triggerAnterior = LOW;

void setup() {
  Serial.begin(9600);
  motor.setSpeed(15);

  pinMode(LED, OUTPUT);
  pinMode(triggerPin, INPUT);
}

void loop() {
  bool triggerActual = digitalRead(triggerPin);

  // Detectar flanco de subida: LOW -> HIGH
  if (triggerActual == HIGH && triggerAnterior == LOW && !esperandoRespuesta) {
    Serial.write('s');
    esperandoRespuesta = true;
  }

  triggerAnterior = triggerActual;

  // Leer respuesta de Python
  if (Serial.available() > 0) {
    char c = Serial.read();

    if (c == 'a') {
      motor.step(1024 / 2);
    }
    else if (c == 'b') {
      motor.step(-2048 / 2);
      esperandoRespuesta = false;   // liberar siguiente ciclo
    }
    else if (c == 'c') {
      motor.step(2048 / 18);
    }
    else if (c == 'd') {
      digitalWrite(LED, HIGH);
    }
    else if (c == 'e') {
      digitalWrite(LED, LOW);
    }
    else if (c == 'f') {
      motor.step(-2048 / 36);
    }
  }
}
