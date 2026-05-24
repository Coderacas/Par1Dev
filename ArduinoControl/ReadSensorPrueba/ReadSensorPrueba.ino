const int pinEntrada = 2;

void setup() {
  Serial.begin(9600);
  pinMode(pinEntrada, INPUT);
}

void loop() {
  int estado = digitalRead(pinEntrada);

  if (estado == HIGH) {
    Serial.println("HIGH");
  } else {
    Serial.println("LOW");
  }

  delay(500);
}
