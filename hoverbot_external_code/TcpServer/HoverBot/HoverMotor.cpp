#include "HoverMotor.h"

#define REF_VOLTAGE 5000
#define MIN_VOLTAGE 300

#define DEFAULT_VOLTAGE 1200

HoverMotor::HoverMotor(int dacAddress, int dirPin, int brakePin, bool forwardHigh)
{
    this->dirPin = dirPin;
    this->brakePin = brakePin;

    pinMode(this->dirPin, OUTPUT);
    pinMode(this->brakePin, OUTPUT);

    this->brake();

    this->forwardHigh = forwardHigh;
    digitalWrite(this->dirPin, this->forwardHigh);

    this->dac.init(dacAddress, REF_VOLTAGE);

    this->setSpeedVoltage(DEFAULT_VOLTAGE);
}

void HoverMotor::setSpeedPercent(float speed)
{
    float speedVoltage = MIN_VOLTAGE + (constrain(speed, 0.0f, 1.0f) * (REF_VOLTAGE - MIN_VOLTAGE));
    this->setSpeedVoltage(speedVoltage);
}

void HoverMotor::setSpeedVoltage(int voltage)
{
    this->dac.outputVoltage(constrain(voltage, MIN_VOLTAGE, REF_VOLTAGE));
}

void HoverMotor::spinForward()
{
    digitalWrite(this->dirPin, this->forwardHigh);
    digitalWrite(this->brakePin, LOW);
}

void HoverMotor::spinBackward()
{
    digitalWrite(this->dirPin, !this->forwardHigh);
    digitalWrite(this->brakePin, LOW);
}

void HoverMotor::brake()
{
    digitalWrite(this->brakePin, HIGH);
}
