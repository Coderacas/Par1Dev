const int led1 = 8;
const int led2 = 9;
const int led3 = 10;
const int led4 = 11;

bool running = false;

void setup() {
  Serial.begin(9600);

  pinMode(led1, OUTPUT);
  pinMode(led2, OUTPUT);
  pinMode(led3, OUTPUT);
  pinMode(led4, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    char input = Serial.read();

    if (input == '1') {
      running = !running;
    }
  }

  if (running) {
    digitalWrite(led1, HIGH);
    delay(500);
    digitalWrite(led1, LOW);

    checkStop();
    if (!running) return;

    digitalWrite(led2, HIGH);
    delay(500);
    digitalWrite(led2, LOW);

    checkStop();
    if (!running) return;

    digitalWrite(led3, HIGH);
    delay(500);
    digitalWrite(led3, LOW);

    checkStop();
    if (!running) return;

    digitalWrite(led4, HIGH);
    delay(500);
    digitalWrite(led4, LOW);

    checkStop();
    if (!running) return;
  }
}

void checkStop() {
  if (Serial.available() > 0) {
    char input = Serial.read();

    if (input == '1') {
      running = false;
    }
  }
}
