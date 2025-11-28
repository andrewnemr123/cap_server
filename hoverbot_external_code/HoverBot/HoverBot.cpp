#include "HoverBot.h"

const bool Bot::hasUltrasonicSwivel = false; // Hover ultrasonic is mounted statically

#define ULTRASONIC_MAX 400 // HC-SR04 rated for 2-400cm
#define OBSTACLE_PING_DELAY_MS 100

HoverBot::HoverBot(int leftDirPin, int leftBrakePin, int rightDirPin, int rightBrakePin,
                    int ultrasonicTriggerPin, int ultrasonicEchoPin, int ultrasonicSensorSafeZone,
                    int ultrasonicServoAngleOffset, int friction)
{
    this->leftMotor = new HoverMotor(MCP4725A0_IIC_Address0, leftDirPin, leftBrakePin);
    this->rightMotor = new HoverMotor(MCP4725A0_IIC_Address1, rightDirPin, rightBrakePin);

    this->ultrasonic = new NewPing(ultrasonicTriggerPin, ultrasonicEchoPin);

    this->ultrasonicSensorSafeZone = ultrasonicSensorSafeZone;
    this->ultrasonicServoAngleOffset = ultrasonicServoAngleOffset;
    this->friction = friction;

    this->id = -1;
    this->seqNum = 0;
}

#pragma region Gets_And_Sets
void HoverBot::setId(int newId)
{
    this->id = newId;
}

int HoverBot::getId()
{
    return this->id;
}

void HoverBot::setSeqNum(int newSeqNum)
{
    this->seqNum = newSeqNum;
}

int HoverBot::getSeqNum()
{
    return this->seqNum;
}

#pragma endregion

bool HoverBot::testDiagnostics()
{
    return true;
}

int HoverBot::forwardWhileCan(int pixels)
{
    int distance = 0;
    this->leftMotor->spinForward();
    this->rightMotor->spinForward();

    distance = this->checkForObstacleWhileMoving(pixels);

    this->leftMotor->brake();
    this->rightMotor->brake();
    return distance;
}

int HoverBot::backwardWhileCan(int pixels)
{
    this->leftMotor->spinBackward();
    this->rightMotor->spinBackward();

    delay(pixels * this->friction);

    this->leftMotor->brake();
    this->rightMotor->brake();
    return pixels;
}

int HoverBot::getSensorPingUltrasonic()
{
    int dist = this->ultrasonic->ping_cm(ULTRASONIC_MAX); // Returns 0 if no echoe (i.e. no obstacle)
    return (dist > 0) ? dist : ULTRASONIC_MAX;
}

bool HoverBot::turnLeftWhileCan(int degrees)
{
    bool result = true;
    this->leftMotor->spinBackward();
    this->rightMotor->spinForward();

    delay(degrees * this->friction);

    this->leftMotor->brake();
    this->rightMotor->brake();
    return result;
}

bool HoverBot::turnRightWhileCan(int degrees)
{
    bool result = true;
    this->leftMotor->spinForward();
    this->rightMotor->spinBackward();

    delay(degrees * this->friction);

    this->leftMotor->brake();
    this->rightMotor->brake();
    return result;
}

bool HoverBot::checkForObstacle()
{
    return this->getSensorPingUltrasonic() <= this->ultrasonicSensorSafeZone; // in cm
}

int HoverBot::checkForObstacleWhileMoving(int targetDistance)
{
    unsigned long startTime = millis();
    unsigned long endTime = startTime + (targetDistance * this->friction);
    // Check for obstacles every OBSTACLE_PING_DELAY_MS
    while ((int)(endTime - millis()) >= OBSTACLE_PING_DELAY_MS)
    {
        unsigned long startLoopTime = millis();
        if (this->checkForObstacle())
        {
            // Return the distance travelled (in ms) if it encounters an object
            return (int)((millis() - startTime) / this->friction);
        }
        int sleepTime = (startLoopTime + OBSTACLE_PING_DELAY_MS) - millis();
        if (sleepTime > 0)
        {
            delay(sleepTime);
        }
    }
    int sleepTime = endTime - millis();
    if (sleepTime > 0)
    {
        delay(sleepTime);
    }

    return targetDistance;
}
