int dataPin = 11;    // DATA / DS / SER
int clockPin = 12;   // REGISTER CLOCK / SH_CP / SRCLK
int latchPin = 8;    // OUTPUT CLOCK / ST_CP / RCLK

int inputPin = 2;    // Sensor / entrada digital

byte secuenciaReg1[] = {
  B00000001,   // a: salida 1
  B00000010,   // b: salidas 1 y 2
  B00000100,   // c: salidas 1, 2 y 3
  B00001000,   // d: salidas 1, 2, 3 y 9
  B00010000,    // e: apagado
  B00000000    // e: apagado  
};

byte secuenciaReg2[] = {
  B00000000,   // a
  B00000000,   // b
  B00000000,   // c
  B00000000,   // d
  B00000001,   // e
  B00000000    // e
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
bool secuenciaActiva = false;

void setup()
{
  pinMode(dataPin, OUTPUT);
  pinMode(clockPin, OUTPUT);
  pinMode(latchPin, OUTPUT);

  pinMode(inputPin, INPUT);

  Serial.begin(9600);

  enviar16(B00000000, B00000000);
  Serial.println("Listo. Sensor HIGH inicia la secuencia.");
}

void loop()
{
  // Si la secuencia NO está activa, espera el sensor
  if (secuenciaActiva == false)
  {
    if (digitalRead(inputPin) == HIGH)
    {
      pasoActual = 0;
      secuenciaActiva = true;

      // Hace la primera combinación automáticamente: "a"
      ejecutarPaso();
      pasoActual = 1;
    }
  }
  else
  {
    // Secuencia ya iniciada: ahora espera "k" para avanzar
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
          secuenciaActiva = false;
          Serial.println("Secuencia terminada.");
        }
      }
    }
  }
}

void ejecutarPaso()
{
  enviar16(secuenciaReg1[pasoActual], secuenciaReg2[pasoActual]);

  delay(25); // 500ms para cada foto
  
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
