/*
  esp32_wifi_test.ino
  Simple ESP32 WiFi connectivity test sketch.

  - Edit WIFI_SSID and WIFI_PASSWORD below (or send credentials over Serial)
  - Compiles for Arduino/PlatformIO ESP32 cores
  - Prints connection progress, IP address, RSSI
  - If connection fails, scans nearby access points and lists them
  - Blinks the onboard LED (GPIO2) when connected

  Created for quick hotspot connectivity testing.
*/

#include <WiFi.h>

// ---- CONFIG: set your hotspot SSID & password here ----
// You can also send: ssid,password over Serial to update at runtime
char WIFI_SSID[64] = "Patwick's Iphone";
char WIFI_PASSWORD[64] = "hello111";
// --------------------------------------------------------

const int LED_PIN = 2;                  // onboard LED for many ESP32 boards
unsigned long connectTimeoutMs = 20000; // 20s connect timeout

void printWiFiStatus()
{
    if (WiFi.isConnected())
    {
        Serial.println("\n== WiFi connected ==");
        Serial.printf("SSID: %s\n", WiFi.SSID().c_str());
        Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("RSSI: %d dBm\n", WiFi.RSSI());
    }
    else
    {
        Serial.println("WiFi not connected");
    }
}

void scanAndPrintAPs()
{
    Serial.println("Scanning nearby WiFi access points...");
    int n = WiFi.scanNetworks();
    if (n == 0)
    {
        Serial.println("No networks found");
        return;
    }
    Serial.printf("Found %d networks:\n", n);
    for (int i = 0; i < n; ++i)
    {
        Serial.printf("%d: %s (RSSI: %d) %s\n", i + 1, WiFi.SSID(i).c_str(), WiFi.RSSI(i), (WiFi.encryptionType(i) == WIFI_AUTH_OPEN) ? "OPEN" : "SECURED");
        delay(10);
    }
}

bool tryConnect(unsigned long timeoutMs)
{
    WiFi.mode(WIFI_STA);
    WiFi.disconnect(true, true);
    delay(100);

    Serial.printf("Attempting to connect to '%s'...\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long start = millis();
    while ((millis() - start) < timeoutMs)
    {
        if (WiFi.status() == WL_CONNECTED)
        {
            return true;
        }
        Serial.print('.');
        delay(500);
    }
    Serial.println();
    return (WiFi.status() == WL_CONNECTED);
}

void setup()
{
    Serial.begin(115200);
    delay(100);
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    Serial.println();
    Serial.println("ESP32 WiFi hotspot test\n");
    Serial.println("You can type: ssid,password and press Enter to update credentials.");

    // Try immediate connect if credentials set
    if (strlen(WIFI_SSID) > 0 && strcmp(WIFI_SSID, "YOUR_SSID_HERE") != 0)
    {
        if (tryConnect(connectTimeoutMs))
        {
            printWiFiStatus();
        }
        else
        {
            Serial.println("Failed to connect within timeout.");
            scanAndPrintAPs();
        }
    }
    else
    {
        Serial.println("No preconfigured SSID found - waiting for Serial input to set credentials.");
        scanAndPrintAPs();
    }
}

unsigned long lastBlink = 0;
bool ledState = false;

void loop()
{
    // Blink LED when connected
    if (WiFi.isConnected())
    {
        if (millis() - lastBlink > 500)
        {
            ledState = !ledState;
            digitalWrite(LED_PIN, ledState ? HIGH : LOW);
            lastBlink = millis();
        }
    }
    else
    {
        // ensure LED off when disconnected
        digitalWrite(LED_PIN, LOW);
    }

    // Handle simple Serial-based credential update: send ssid,password\n
    if (Serial.available())
    {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.length() > 0)
        {
            int comma = line.indexOf(',');
            if (comma > 0)
            {
                String s = line.substring(0, comma);
                String p = line.substring(comma + 1);
                s.trim();
                p.trim();
                s.toCharArray(WIFI_SSID, sizeof(WIFI_SSID));
                p.toCharArray(WIFI_PASSWORD, sizeof(WIFI_PASSWORD));
                Serial.printf("New credentials set: '%s' / '%s'\n", WIFI_SSID, WIFI_PASSWORD);
                Serial.println("Attempting to connect...");
                if (tryConnect(connectTimeoutMs))
                {
                    printWiFiStatus();
                }
                else
                {
                    Serial.println("Failed to connect.");
                    scanAndPrintAPs();
                }
            }
            else if (line.equalsIgnoreCase("status"))
            {
                printWiFiStatus();
            }
            else if (line.equalsIgnoreCase("scan"))
            {
                scanAndPrintAPs();
            }
            else
            {
                Serial.println("Unrecognized command. Use: ssid,password  OR 'scan' OR 'status'");
            }
        }
    }

    delay(10);
}
