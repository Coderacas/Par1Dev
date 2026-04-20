const int numLEDs = 4;
int ledPins[numLEDs] = {8, 9, 10, 11};
bool ledState[numLEDs] = {false, false, false, false};

void setup() {
  Serial.begin(9600);

  for (int i = 0; i < numLEDs; i++) {
    pinMode(ledPins[i], OUTPUT);
  }

  Serial.println("Send 1, 2, 3 or 4");
}

void loop() {
  int inputValue = getInput();   // get input from wherever
  if (inputValue != 0) {
    toggleLED(inputValue);
    printStates();
  }
}

int getInput() {
  if (Serial.available() > 0) {
    char input = Serial.read();

    if (input >= '1' && input <= '4') {
      return input - '0';   // converts '1' to 1, '2' to 2, etc.
    }
  }

  return 0;   // no valid input
}

void toggleLED(int ledNumber) {
  int index = ledNumber - 1;

  ledState[index] = !ledState[index];
  digitalWrite(ledPins[index], ledState[index]);
}

void printStates() {
  for (int i = 0; i < numLEDs; i++) {
    Serial.print("LED ");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(ledState[i] ? "ON" : "OFF");

    if (i < numLEDs - 1) {
      Serial.print(" / ");
    }
  }
  Serial.println();
}
