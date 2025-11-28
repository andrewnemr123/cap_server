# ESP32 WiFi Hotspot Test

Files added:
- `esp32_wifi_test.ino` — Arduino-compatible sketch to test connecting to a WiFi hotspot.

Quick steps
1. Open `esp32_wifi_test.ino` in Arduino IDE or PlatformIO.
2. Edit the top of the file to set `WIFI_SSID` and `WIFI_PASSWORD` (or leave blank and send credentials over Serial).
3. Compile and flash to your ESP32 board.
4. Open Serial Monitor at 115200 baud and observe logs.

Arduino IDE (Windows) instructions
1. Install Arduino IDE and the ESP32 board support:
   - In Arduino IDE: File → Preferences → Additional Boards Manager URLs, add:
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   - Tools → Board → Boards Manager → search for "esp32" → install "esp32 by Espressif Systems".
2. Select your ESP32 board (Tools → Board) and correct COM port (Tools → Port).
3. Open `esp32_wifi_test.ino`, set SSID/password, click Upload.
4. Open Serial Monitor (Tools → Serial Monitor) at 115200 baud.

PlatformIO (VS Code) instructions
1. Install PlatformIO extension for VS Code.
2. Create a new PlatformIO project for your ESP32 board, or use an existing project.
3. Copy `esp32_wifi_test.ino` into the project's `src/` folder (rename to `main.cpp` if you prefer).
4. Edit `platformio.ini` to match your board (e.g., `board = esp32dev`).
5. Build and Upload from PlatformIO.
6. Open the Serial Monitor from PlatformIO at 115200 baud.

Using Serial to send credentials
- If you prefer not to edit the file, open Serial Monitor at 115200 baud and send a single line with:

  ssid,password

  For example: MyPhoneHotspot,supersecretpassword

Commands available over Serial
- ssid,password — set new credentials and attempt connect
- scan — scan and list nearby WiFi networks
- status — print current connection status

Validation checklist
- On successful connect you should see:
  - "== WiFi connected =="
  - IP address line (e.g., IP: 192.168.43.123)
  - RSSI value (signal strength in dBm)
  - Onboard LED blinking
- If connection fails:
  - Sketch prints "Failed to connect" and lists nearby networks
  - Verify hotspot SSID/password, ensure hotspot allows client connections (no MAC filtering)
  - Some phone hotspots require you to enable visibility or accept client devices — check phone settings

Troubleshooting tips
- Ensure the phone hotspot is on and not using an exotic band (try 2.4 GHz if available).
- If using WPA3 or enterprise settings, try switching to WPA2/Open for testing.
- Try moving the ESP32 closer to the hotspot for a stronger signal.
- If the board doesn't appear in Arduino/PlatformIO, install correct USB driver (CP210x or CH340) depending on your board.

Next steps (optional)
- Add mDNS or HTTP client code to verify internet connectivity and DNS resolution.
