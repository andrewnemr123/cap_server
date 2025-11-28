int SC = A5; // Brown Wire   -   Speed Pulse Signal Output
int ZF = 10; // Blue Wire    -   Forward Reverse Controlling
int VR = 11; // White Wire   -   Speed Input

int speedSignal;

void setup()
{
  // put your setup code here, to run once:
  pinMode(SC, OUTPUT);
  pinMode(ZF, OUTPUT);
  pinMode(VR, OUTPUT);

  Serial.begin(9600);
}

void loop()
{
  // put your main code here, to run repeatedly:
  speedSignal = analogRead(SC);
  analogWrite(ZF, 255);
  analogWrite(VR, 255);

  for (int i = 0; i < 256; i++)
  {
    analogWrite(VR, i);
    Serial.println(speedSignal);
    delay(10);
  }

  for (int i = 255; i > -1; i--)
  {
    analogWrite(VR, i);
    Serial.println(speedSignal);
    delay(10);
  }
}