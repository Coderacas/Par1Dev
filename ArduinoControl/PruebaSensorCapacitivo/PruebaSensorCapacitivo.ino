const int sensorPin = 2;

void setup() {
  pinMode(sensorPin, INPUT);
  Serial.begin(9600);
}

void loop() {
  int estado = digitalRead(sensorPin);

  if (estado == HIGH) {
    Serial.println("Sensor: HIGH");
  } else {
    Serial.println("Sensor: LOW");
  }

  delay(200);
}
