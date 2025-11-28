# esp32_wifi_test_idf

This is an ESP-IDF project converted from an Arduino-style sketch. It attempts to connect to a hotspot, prints status, scans nearby APs, and blinks the onboard LED when connected.

Build & flash (Espressif VS Code extension)
1. Install the Espressif IDF extension and run the "Configure ESP-IDF" wizard (it will install toolchain and Python environment).
2. Open this folder in VS Code (Open Folder -> select the folder that contains CMakeLists.txt).
3. Use the extension commands (Command Palette):
   - "ESP-IDF: Build"
   - "ESP-IDF: Flash (choose COM port)"
   - "ESP-IDF: Monitor"

Build & flash (command line) — PowerShell example
1. Run the export script produced by your IDF install (replace path if different):

```powershell
# Example — adjust path to your esp-idf install
&C:\esp\esp-idf\export.ps1
idf.py -p COM5 build
idf.py -p COM5 flash
idf.py -p COM5 monitor
```

Replace COM5 with the COM port of your board.

Serial commands
- Send `ssid,password` to update credentials and attempt connection.
- `scan` to list nearby access points.
- `status` to print current connection status.

Notes
- This project uses ESP-IDF APIs and is intended to be built using idf.py / Espressif extension. If you prefer Arduino core, use the original `.ino` file.