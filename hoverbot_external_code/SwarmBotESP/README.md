# SwarmBotESP

## Setting up development environment with ESP32

1. Download and install USB-UART bridge drivers from [CP210x USB to UART Bridge VCP Drivers](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers?tab=downloads)
    - Follow instructions in the release notes to install (on Windows, right click on `silabser.inf` file and click "Install")
    - It is possible that your model of the board uses a different USB-to-UART bridge than HoverBotESP. In that case, follow the detailed instruction from [Establish Serial Connection with ESP32](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/establish-serial-connection.html)
2. (Recommended for Windows) Download and install Espressif-IDE from [ESP-IDF Windows Installer Download](https://dl.espressif.com/dl/esp-idf/)
    - The IDE has a bug where the C Indexer would stop working sometimes, making a lot of errors appear in the text editor (but still compiles). To avoid this bug, **close the project before closing the IDE** and reopen the project when you start the IDE, then build the project. (Note: for any newly created or imported projects, you need to build the project first before the indexer starts to work)
    - For Mac and Linux, and Windows if you do not want to use the Espressif-IDE, follow instructions from [Getting Started with ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/get-started/index.html)

    **It's highly recommended that you follow through [Getting Started with ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/get-started/index.html) either way and experiment yourself with a new project before start working on the existing SwarmBotESP projects.**

3. Import or create a new project by selecting "Espressif IDF Project"
4. Finding the COM port on windows:
    - Go to This PC/Manage and find CP210 under USB/COM ports
    - Alternatively, select it from the drop down menu in Espressif-IDE's build target selection
5. When flashing (i.e. uploading code) to the board, if the board refuses to connect, then the board is in the wrong boot mode. To force the board into the correct boot mode:
    - When flashing, once the terminal displays "connecting", hold the "Boot" button on the board

## Using SerialTool to monitor the robot

### Setup

SerialTool is a Python-based utility for serial communication with ESP32-based robots. It supports both monitoring and configuration modes.

#### Prerequisites
- Python 3.11 or higher
- pyserial package

#### Installation

Navigate to the SerialTool directory:
```bash
cd Servers/SwarmBotESP/SerialTool
```

**Option 1: Using global pyserial (simpler)**
```bash
pip install pyserial
```

**Option 2: Using virtual environment (recommended for development)**
```bash
python -m pip install virtualenv
python -m virtualenv venv

# Windows:
.\venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

# Install dependencies:
python -m pip install -r requirements.txt
```

### Monitor Mode

Monitor mode allows you to view serial output from the robot in real-time.

```bash
# Auto-detect port
python main.py -m

# Specify port explicitly
python main.py --port COM3 -m
```

**Controls:**
- `Ctrl + ]` to quit serial monitor
- `Ctrl + T` for menu

### Debug Mode

Enable verbose debug messages:
```bash
python main.py -d
python main.py --port COM3 -d
```

### Command-line Options

- `--port <PORT>` - Specify serial port (e.g., COM3 on Windows, /dev/ttyUSB0 on Linux)
- `--baudrate <RATE>` - Set baudrate (default: 115200)
- `-m, --monitor` - Enter serial monitor mode
- `-d, --debug` - Enable debug logging
- `-h, --help` - Show help message

## Using SerialTool to configure the robot

### Configuration Mode

Configuration mode allows you to set WiFi credentials and server connection parameters.

1. Connect the ESP32 board via USB
2. Run SerialTool in configuration mode:
   ```bash
   python main.py
   # or specify port:
   python main.py --port COM3
   ```
3. When prompted "Reboot the board", press the **EN button** on the ESP32
4. Enter configuration commands when prompted

### Configuration Commands

| Command | Description | Example |
|---------|-------------|----------|
| `reset` | Reset all stored values to defaults | `reset` |
| `set ssid <SSID>` | Set WiFi network name | `set ssid MyNetwork` |
| `set pwd <PASSWORD>` | Set WiFi password | `set pwd MyPassword123` |
| `set server_host <IP>` | Set Swarm Server IPv4 address | `set server_host 192.168.1.139` |
| `set server_port <PORT>` | Set server port number | `set server_port 3000` |
| `set identity <NAME>` | Set robot identity/name | `set identity HOVERBOT` |
| `done configuration` | Exit configuration mode | `done configuration` |

### Configuration Example

```bash
$ python main.py --port COM3
[2025-12-02 10:30:15.123] [INFO] Using serial port COM3
[2025-12-02 10:30:15.234] [INFO] Reboot the board. Waiting for configure request
# Press EN button on ESP32
[2025-12-02 10:30:18.456] [INFO] Tool Received: UART_MAGIC_ROBOT; ready
Command to send: set ssid RoboticsLab
[2025-12-02 10:30:22.123] [INFO] Tool Sending: UART_MAGIC_TOOL; set ssid RoboticsLab
Command to send: set pwd SecurePassword123
[2025-12-02 10:30:25.234] [INFO] Tool Sending: UART_MAGIC_TOOL; set pwd SecurePassword123
Command to send: set server_host 192.168.1.100
[2025-12-02 10:30:28.345] [INFO] Tool Sending: UART_MAGIC_TOOL; set server_host 192.168.1.100
Command to send: set server_port 3000
[2025-12-02 10:30:31.456] [INFO] Tool Sending: UART_MAGIC_TOOL; set server_port 3000
Command to send: set identity HOVERBOT_01
[2025-12-02 10:30:34.567] [INFO] Tool Sending: UART_MAGIC_TOOL; set identity HOVERBOT_01
Command to send: done configuration
[2025-12-02 10:30:37.678] [INFO] Tool Received: UART_MAGIC_ROBOT; configuration saved
[2025-12-02 10:30:37.789] [INFO] Closed serial connection
```

## Future Improvements

TODO