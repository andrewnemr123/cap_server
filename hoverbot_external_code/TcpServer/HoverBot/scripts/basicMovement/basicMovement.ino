#include "DFRobot_MCP4725.h"
#include <NewPing.h>
#define REF_VOLTAGE 5000

NewPing sonar1(10, 11, 35); // trigger pin, echo pin, distances
DFRobot_MCP4725 DAC1;       // 8 side
DFRobot_MCP4725 DAC2;       // 5 side/battery side

// voltage always 0 or >= 300
uint16_t OUTPUT_VOLTAGER = 650; // Input DAC output voltage (0~REF_VOLTAGE,unit: mV)
uint16_t OUTPUT_VOLTAGEL = 700;

int breakPin1 = 12; // right
int breakPin2 = 4;  // right wheel
int dirPin1 = 2;    // set on HIGH to go straight (left wheel)
int dirPin2 = 7;    // Set on LOW to go straight (right wheel)

void setup()
{

  // put your setup code here, to run once:
  Serial.begin(115200);
  /* MCP4725A0_address is 0x60 or 0x61
   * MCP4725A0_IIC_Address0 -->0x60
   * MCP4725A0_IIC_Address1 -->0x61
   */

  pinMode(breakPin1, OUTPUT);
  pinMode(breakPin2, OUTPUT);
  pinMode(dirPin1, OUTPUT);
  pinMode(dirPin2, OUTPUT);

  digitalWrite(breakPin1, HIGH);
  digitalWrite(breakPin2, HIGH);

  DAC1.init(MCP4725A0_IIC_Address0, REF_VOLTAGE);
  DAC2.init(MCP4725A0_IIC_Address1, REF_VOLTAGE);
}

void turn();
void moveWithSensors();
void goStraight();
void goBackward();

void loop()
{

  //goStraight();

  delay(5000);

  digitalWrite(breakPin1, LOW);
  digitalWrite(breakPin2, LOW);

  DAC1.outputVoltage(600);
  DAC2.outputVoltage(600);

  delay(5000);

  digitalWrite(breakPin1, HIGH);
  digitalWrite(breakPin2, HIGH);
}

void turn()
{
  // first check which direction to turn
  // if no turn possible go backward until a turn is possible

  Serial.println("Turning");
  digitalWrite(dirPin1, HIGH);
  digitalWrite(dirPin2, LOW);
  digitalWrite(breakPin1, LOW);
  digitalWrite(breakPin2, LOW);
}

void goStraight()
{
  Serial.println("Going Straight");
  digitalWrite(dirPin1, LOW);
  digitalWrite(dirPin2, LOW);
  digitalWrite(breakPin1, LOW);
  digitalWrite(breakPin2, LOW);
}

void goBackward()
{
  Serial.println("Going Back");
  digitalWrite(dirPin1, HIGH);
  digitalWrite(dirPin2, HIGH);
  digitalWrite(breakPin1, LOW);
  digitalWrite(breakPin2, LOW);
}

void moveWithSensors()
{

  while (sonar1.ping_cm() > 0)
  {
    digitalWrite(breakPin1, HIGH);
    digitalWrite(breakPin2, HIGH);
    delay(1000);
  }

  goStraight();
}
