#ifndef Motor_H
#define Motor_H

#include "DFRobot_MCP4725.h"

class HoverMotor
{
    DFRobot_MCP4725 dac;

    bool forwardHigh;

    int dirPin;
    int brakePin;

public:
    HoverMotor(int dacAddress, int dirPin, int brakePin, bool forwardHigh = false);
    void setSpeedPercent(float speed);
    void setSpeedVoltage(int voltage);
    void spinForward();
    void spinBackward();
    void brake();
};

#endif
