int dataPin = 11;    // DATA / DS / SER
int clockPin = 12;   // REGISTER CLOCK / SH_CP / SRCLK
int latchPin = 8;    // OUTPUT CLOCK / ST_CP / RCLK

byte secuenciaReg1[] = {
  B00000001,   // a
  B00000010,   // b
  B00000100,   // c
  B00001000,   // d
  B00010000,   // e
  B00000000    // f
};

byte secuenciaReg2[] = {
  B00000000,   // a
  B00000000,   // b
  B00000000,   // c
  B00000000,   // d
  B00000001,   // e
  B00000000    // f
};

char mensajes[] = {
  'a',
  'b',
  'c',
  'd',
  'e',
  'f'
};

int pasoActual = 0;
int totalPasos = 6;

void setup()
{
  pinMode(dataPin, OUTPUT);
  pinMode(clockPin, OUTPUT);
  pinMode(latchPin, OUTPUT);

  Serial.begin(9600);

  enviar16(B00000000, B00000000);
  Serial.println("Listo. Envia 'k' por Serial para avanzar la secuencia.");
}

void loop()
{
  if (Serial.available() > 0)
  {
    char dato = Serial.read();

    if (dato == 'k')
    {
      ejecutarPaso();
      pasoActual++;

      if (pasoActual >= totalPasos)
      {
        pasoActual = 0;
        Serial.println("Secuencia terminada. Envia 'k' para iniciar de nuevo.");
      }
    }
  }
}

void ejecutarPaso()
{
  enviar16(secuenciaReg1[pasoActual], secuenciaReg2[pasoActual]);

  delay(25); // Tiempo para cada foto
  
  Serial.println(mensajes[pasoActual]);
}

void enviar16(byte registro1, byte registro2)
{
  digitalWrite(latchPin, LOW);

  // Primero se manda el segundo registro
  shiftOut(dataPin, clockPin, MSBFIRST, registro2);

  // Luego se manda el primero
  shiftOut(dataPin, clockPin, MSBFIRST, registro1);

  digitalWrite(latchPin, HIGH);
}
