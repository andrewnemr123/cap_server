#ifndef HoverBot_H
#define HoverBot_H

#include "Shared/Bot.h"
#include "HoverMotor.h"

#include <NewPing.h>

class HoverBot: public Bot
{
    HoverMotor *leftMotor;
    HoverMotor *rightMotor;

    NewPing *ultrasonic;

public:
    HoverBot(int leftDirPin, int leftBrakePin, int rightDirPin, int rightBrakePin,
        int ultrasonicTriggerPin, int ultrasonicEchoPin, int ultrasonicSensorSafeZone, double friction);
    int getId();
    void setId(int id);
    int getSeqNum();
    void setSeqNum(int seqNum);
    void setMotorConstants(int leftWheelPower, int rightWheelPower);

    bool testDiagnostics();
    int forwardWhileCan(int pixels);
    int backwardWhileCan(int pixels);
    bool turnLeftWhileCan(int degrees);
    bool turnRightWhileCan(int degrees);
    int getSensorPingUltrasonic();

#pragma region Unsupported_Methods
    void setUltrasonicServoAngleOffset(int newUltrasonicServoAngleOffset) { return; }
    int getUltrasonicServoAngleOffset() { return 0; }
    bool turnUltrasonicSensor(int degrees) { return false ; }
    int* getSensorSweepUltrasonic() { return 0; };
#pragma endregion

private:
    int checkForObstacleWhileMoving(int targetDistance);
    bool checkForObstacle();
};

#endif
