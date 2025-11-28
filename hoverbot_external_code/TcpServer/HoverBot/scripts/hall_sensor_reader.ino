int HA = A0; // Feedback from phase 1 power connection
int HB = A1; // Feedback from phase 2 power connection
int HC = A2; // Feedback from phase 3 power connection

int valueA, valueB, valueC = -4000;
int clk = 0;

void setup()
{
  // put your setup code here, to run once:
  Serial.begin(9600);
}

void loop()
{
  // put your main code here, to run repeatedly:
  valueA = analogRead(HA);
  valueB = analogRead(HB);
  valueC = analogRead(HC);

  char output[150];
  sprintf(output, "Hall Sensor Reading %d : HA = %d; HB = %d; HC = %d", clk, valueA, valueB, valueC);
  Serial.println(output);
  delay(500);

  Serial.println(valueA);
  delay(10);
  ++clk;
}