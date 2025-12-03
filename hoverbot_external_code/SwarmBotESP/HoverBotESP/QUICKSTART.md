# ESP32 HoverBot - Quick Start Guide

## 🚀 Setup & Run

### 1. Build & Flash ESP32 Firmware

```bash
cd ~/capstone/hoverbot/SwarmBotESP/HoverBotESP 

source $HOME/esp/v5.5.1/esp-idf/export.sh && idf.py fullclean
# Build the firmware
./build.sh

# Flash to ESP32 (based on the usb port chnage for what you have)
idf.py -p /dev/tty.usbserial-140 flash monitor

# With debug logging enabled:
idf.py -p /dev/tty.usbserial-140 flash monitor -D DEBUG_MODE=1
```

### 2. Start the Python Server

```bash
cd ~/capstone/swarm-server
source .venv/bin/activate
python3 -m src.llm.server
```

### 3. Basic Commands

```bash
# List connected robots
list

# View sensor data
sensors

# Send movement commands
0                    # Select robot 0
forward 2000         # Move forward for 2000ms
backward 1000        # Move backward for 1000ms
left 500             # Rotate left for 500ms
right 500            # Rotate right for 500ms
ping                 # Get ultrasonic sensor reading
```

## 🐛 Debugging

### Enable Verbose Logging

```bash
# Flash with debug mode
idf.py -p /dev/tty.usbserial-140 flash monitor -D DEBUG_MODE=1

# Monitor only (after flashing)
idf.py -p /dev/tty.usbserial-140 monitor

# Filter logs by component
idf.py -p /dev/tty.usbserial-140 monitor | grep "TCP:"
idf.py -p /dev/tty.usbserial-140 monitor | grep "WIFI:"
```

### Monitor UDP Packets

```bash
# Capture UDP sensor data on port 3001
sudo tcpdump -i en0 -n udp port 3001 -X

# Or use Python listener
python3 -c "
import socket, json
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', 3001))
print('Listening on UDP 3001...')
while True:
    data, addr = s.recvfrom(512)
    print(f'{addr[0]}: {json.loads(data)}')
"
```

### Check Serial Connection

```bash
# List available serial ports
ls /dev/tty.usb*

# Connect to serial console
screen /dev/tty.usbserial-140 115200

# Exit screen: Ctrl+A then K then Y
```

## ⚙️ Configuration

### WiFi Settings (via Serial UART)

```bash
# Connect to serial console
screen /dev/tty.usbserial-140 115200

# Send configuration commands
UART_MAGIC_TOOL;set ssid YourNetworkName
UART_MAGIC_TOOL;set pwd YourPassword
UART_MAGIC_TOOL;set server_host 192.168.1.100
UART_MAGIC_TOOL;set server_port 3000
UART_MAGIC_TOOL;set identity HOVERBOT
UART_MAGIC_TOOL;done configuration

# Press ESP32 reset button to apply
```

## 🔧 Troubleshooting

**WiFi not connecting:**
```bash
# Check current settings
idf.py -p /dev/tty.usbserial-140 monitor
# Look for "SSID:" and "Password:" in startup logs

# Reconfigure via serial (see Configuration section)
```

**Can't find serial port:**
```bash
ls /dev/tty.usb*
# If nothing, check USB cable or drivers
```

**Build errors:**
```bash
# Clean and rebuild
idf.py fullclean
idf.py build
```

**Sensor reads 0 cm:**
- Check wiring: TRIG pin 18, ECHO pin 19
- Verify 5V power to sensor

**No UDP data arriving:**
- Check server is listening on port 3001
- Verify firewall allows UDP traffic

## 📚 Documentation

- [README_HYBRID_PROTOCOL.md](README_HYBRID_PROTOCOL.md) - Protocol details
- [README.md](README.md) - Full project documentation
- [ESP-IDF Docs](https://docs.espressif.com/projects/esp-idf/en/latest/)
