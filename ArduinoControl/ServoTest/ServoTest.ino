// =====================================================
// PRUEBA AISLADA DE SERVO
// =====================================================
// Comandos por Serial Monitor a 9600 baud:
//   b = BUENA -> 120 grados
//   m = MALA  -> 60 grados
//   c = CENTRO -> 90 grados
//
// El servo nunca va a 0 ni a 180.

#include <Servo.h>

const int pinServo = 9;

const int SERVO_CENTRO = 90;
const int SERVO_DELTA  = 30;
const int SERVO_BUENA  = SERVO_CENTRO + SERVO_DELTA;
const int SERVO_MALA   = SERVO_CENTRO - SERVO_DELTA;

Servo servoClasificador;

void moverServoSeguro(int angulo)
{
  angulo = constrain(angulo, SERVO_CENTRO - SERVO_DELTA, SERVO_CENTRO + SERVO_DELTA);
  servoClasificador.write(angulo);

  Serial.print("SERVO_ANGULO=");
  Serial.println(angulo);
}

void setup()
{
  Serial.begin(9600);

  servoClasificador.attach(pinServo);
  moverServoSeguro(SERVO_CENTRO);

  Serial.println("PRUEBA_SERVO_LISTA");
  Serial.println("b=BUENA, m=MALA, c=CENTRO");
}

void loop()
{
  if (Serial.available() <= 0) return;

  char dato = Serial.read();

  delay(5);
  while (Serial.available() > 0) Serial.read();

  if (dato == '\r' || dato == '\n') return;

  if (dato == 'b')
  {
    moverServoSeguro(SERVO_BUENA);
    Serial.println("SERVO_BUENA");
  }
  else if (dato == 'm')
  {
    moverServoSeguro(SERVO_MALA);
    Serial.println("SERVO_MALA");
  }
  else if (dato == 'c')
  {
    moverServoSeguro(SERVO_CENTRO);
    Serial.println("SERVO_CENTRO");
  }
  else
  {
    Serial.println("COMANDO_INVALIDO");
  }
}
