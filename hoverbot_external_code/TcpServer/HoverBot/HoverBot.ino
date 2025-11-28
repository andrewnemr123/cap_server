#include "Shared/SwarmCommandHandler.h"
#include "Shared/SwarmCommandHandler.cpp" // Linker workaround
#include "Shared/Bot.h"

#include "HoverBot.h"

SoftwareSerial sserial(8, 9); // RX, TX
SwarmCommandHandler *commandHandler;

const int leftBrakePin = 12;
const int rightBrakePin = 4;
const int leftDirPin = 2;
const int rightDirPin = 7;
const int ultrasonicTriggerPin = 10;
const int ultrasonicEchoPin = 11;
const int ultrasonicSensorSafeZone = 8; // in cm
const int ultrasonicServoAngleOffset = 0;
const int friction = 6;

void setup()
{
    Serial.begin(9600);
    Serial.println(F("Print setup"));
    Bot *bot = new HoverBot(leftDirPin, leftBrakePin, rightDirPin, rightBrakePin,
                    ultrasonicTriggerPin, ultrasonicEchoPin, ultrasonicSensorSafeZone,
                    ultrasonicServoAngleOffset, friction);
    commandHandler = new SwarmCommandHandler(&sserial, 7, bot, &Serial);
}

void loop()
{
    commandHandler->getCommands();
}
