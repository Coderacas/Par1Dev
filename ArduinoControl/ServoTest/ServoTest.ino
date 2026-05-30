#include <Servo.h>

Servo servo;

const int PIN_SERVO = 9;

void setup()
{
  Serial.begin(9600);
  servo.attach(PIN_SERVO);
  servo.write(90);

  Serial.println("Servo listo");
  Serial.println("b=120, m=60, c=90");
}

void loop()
{
  if (!Serial.available()) return;

  char comando = Serial.read();

  if (comando == 'b')
  {
    servo.write(120);
    Serial.println("120");
  }
  else if (comando == 'm')
  {
    servo.write(60);
    Serial.println("60");
  }
  else if (comando == 'c')
  {
    servo.write(90);
    Serial.println("90");
  }
}
