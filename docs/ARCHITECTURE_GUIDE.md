# Complete System Architecture: HoverBot Swarm Control

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Repository Structure](#repository-structure)
3. [Communication Flow](#communication-flow)
4. [Component Deep Dive](#component-deep-dive)
5. [Protocol Specifications](#protocol-specifications)
6. [Setup & Deployment](#setup--deployment)

---

## System Overview

This is a **distributed robot control system** consisting of:

- **Python Server** (`src/` folder): TCP/UDP hybrid server for command dispatching and sensor aggregation
- **ESP32 Firmware** (`hoverbot_external_code/SwarmBotESP/HoverBotESP/`): Embedded C code running on ESP32-WROVER-E
- **Command Parsers**: Protocol adapters for different robot types (R1D4, HOVERBOT)
- **Optional AI Integration**: Voice commands via OpenAI, navigation via map system

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        PYTHON SERVER                            │
│                   (macOS/Linux/Windows)                         │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   TCP:3000   │  │   UDP:3001   │  │    STDIN     │         │
│  │   Commands   │  │ Sensor Data  │  │  (Manual)    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│  ┌──────┴──────────────────┴──────────────────┴───────┐        │
│  │         RobotServer (asyncio)                      │        │
│  │  - parse_and_send_to()                             │        │
│  │  - parse_and_broadcast()                           │        │
│  │  - _handle_sensor_data()                           │        │
│  └────────────────────────────────────────────────────┘        │
│         │                  │                                    │
│  ┌──────┴───────┐   ┌──────┴──────┐                            │
│  │ R1D4Parser   │   │ HOVERParser │                            │
│  │ move/turn    │   │ FORWARD/... │                            │
│  └──────────────┘   └─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                       │                  │
                    TCP:3000          UDP:3001
                       │                  │
                       ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ESP32 FIRMWARE                             │
│                   (FreeRTOS on ESP32)                           │
│                                                                 │
│  ┌────────────────┐                    ┌──────────────────┐    │
│  │  tcp_client()  │◄───WiFi Events────►│  fast_scan()     │    │
│  │  (Core 1)      │                    │  event_handler() │    │
│  └────────┬───────┘                    └──────────────────┘    │
│           │                                                     │
│     ┌─────┴──────────────┐                                     │
│     │  Command Receiver  │                                     │
│     │  - Parse JSON      │                                     │
│     │  - Execute Action  │                                     │
│     │  - Send Response   │                                     │
│     └─────┬──────────────┘                                     │
│           │                                                     │
│  ┌────────┴──────────┐          ┌─────────────────────┐        │
│  │  Motor Driver     │          │ udp_sensor_stream() │        │
│  │  - move_forward() │          │     (Core 0)        │        │
│  │  - rotate_left()  │          │  - us_ping()        │        │
│  │  - us_ping()      │          │  - Send UDP @ 10Hz  │        │
│  └───────────────────┘          └─────────────────────┘        │
│           │                               │                     │
│  ┌────────┴───────────────────────────────┴──────────┐         │
│  │              GPIO / Hardware                       │         │
│  │  - Left/Right Motors (DIR, STOP pins)             │         │
│  │  - Ultrasonic Sensor (TRIG, ECHO pins)            │         │
│  │  - LED Indicator                                   │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
swarm-server/
├── src/                              # Python server code
│   ├── llm/                          # Language model & command processing
│   │   ├── server.py                 # Main TCP/UDP server (hybrid)
│   │   ├── command_parser.py        # R1D4 & HOVERBOT protocol parsers
│   │   ├── voice_command_interpreter.py  # OpenAI NLP integration
│   │   ├── robot_navigator.py       # Visual SLAM (SIFT-based)
│   │   ├── stt/                     # Speech-to-text (Whisper)
│   │   └── tts/                     # Text-to-speech (NixTTS)
│   └── map/
│       └── mapStructure.py          # Graph-based navigation (Dijkstra)
│
├── hoverbot_external_code/
│   └── SwarmBotESP/
│       └── HoverBotESP/              # ESP32 firmware (ESP-IDF project)
│           ├── main/
│           │   ├── main.c            # Core firmware logic
│           │   ├── main.h            # Configuration constants
│           │   ├── motor_driver.c    # Hardware control
│           │   └── motor_driver.h    # GPIO pinout definitions
│           ├── build.sh              # Automated build script
│           ├── QUICKSTART.md         # ESP32 setup guide
│           └── README_HYBRID_PROTOCOL.md  # Protocol documentation
│
├── examples/
│   └── hybrid_client.py             # Python test client (simulates robot)
│
├── docs/
│   ├── HYBRID_PROTOCOL.md           # TCP/UDP protocol specification
│   ├── ESP32_WIFI_TROUBLESHOOTING.md
│   └── ARCHITECTURE_GUIDE.md        # This file
│
└── requirements.txt                 # Python dependencies
```

---

## Communication Flow

### Startup Sequence

```
1. ESP32 Powers On
   ├─► Initialize NVS (load WiFi/server config)
   ├─► Configure GPIO pins (motors, sensors)
   ├─► Start WiFi scan (fast_scan())
   └─► Wait for IP assignment

2. WiFi Connected (IP_EVENT_STA_GOT_IP)
   └─► Launch tcp_client()
       ├─► Connect to server TCP:3000
       ├─► Send registration: "HOVERBOT\n"
       ├─► Create UDP socket → server:3001
       └─► Spawn udp_sensor_stream_task (Core 0)

3. Python Server
   ├─► Accepts TCP connection
   ├─► Receives registration message
   ├─► Assigns HOVERBOTCommandParser
   └─► Waits for manual/voice commands
```

### Command Execution Flow

```
┌─────────────┐
│ User Types: │  "0"  →  "forward 2.5"
│   Server    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│ Server: _stdin_router()      │
│ 1. Select client [0]         │
│ 2. Get parser (HOVERBOT)     │
│ 3. Parse "forward 2.5"       │
└──────┬───────────────────────┘
       │
       ▼ TCP:3000
┌──────────────────────────────────────────────────┐
│ HOVERBOTCommandParser.parse_command()            │
│ Input:  "forward 2.5"                            │
│ Output: {"command":"FORWARD","floatData":[2500], │
│          "intData":[],"status":"DISPATCHED",...} │
└──────┬───────────────────────────────────────────┘
       │
       ▼ (JSON over TCP)
┌──────────────────────────────┐
│ ESP32: tcp_client()          │
│ 1. recv() JSON from socket   │
│ 2. cJSON_Parse()             │
│ 3. Extract command="FORWARD" │
│ 4. Extract floatData[0]=2500 │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ ESP32: Execute Command       │
│ move_forward(2500ms)         │
│ - Set motor direction pins   │
│ - Disengage stop pins        │
│ - vTaskDelay(2500)           │
│ - Engage stop pins           │
└──────┬───────────────────────┘
       │
       ▼ TCP:3000
┌──────────────────────────────────────────────────┐
│ ESP32: Build Response                            │
│ {"id":0,"command":"FORWARD","status":"SUCCESS", │
│  "result":2500.0,"text":""}                      │
└──────┬───────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Server: _handle_client()     │
│ Log: "📥 From (IP): {...}"   │
└──────────────────────────────┘
```

### Sensor Data Streaming (UDP)

```
ESP32 Core 0                         Server
┌──────────────────┐                 ┌──────────────────┐
│udp_sensor_stream │                 │ UDPProtocol      │
│                  │                 │ .datagram_recv() │
└────────┬─────────┘                 └────────▲─────────┘
         │                                     │
    ┌────▼────┐                                │
    │ 100ms   │ (10 Hz loop)                  │
    │ delay   │                                │
    └────┬────┘                                │
         │                                     │
    ┌────▼──────────────┐                      │
    │ us_ping()         │                      │
    │ → distance_cm=42  │                      │
    └────┬──────────────┘                      │
         │                                     │
    ┌────▼──────────────────────────┐          │
    │ cJSON_CreateObject()          │          │
    │ {"type":"proximity",          │          │
    │  "timestamp":1234.56,         │          │
    │  "distance_cm":42,            │          │
    │  "robot_id":"HOVERBOT"}       │          │
    └────┬──────────────────────────┘          │
         │                                     │
    ┌────▼──────────────┐                      │
    │ sendto(udp_sock,  │  UDP:3001           │
    │   json_str, ...)  ├─────────────────────┘
    └───────────────────┘
                                    ┌──────────────────┐
                                    │ Server stores in │
                                    │ _sensor_data{}   │
                                    │ with timestamp   │
                                    └──────────────────┘
```

---

## Component Deep Dive

### 1. Python Server (`src/llm/server.py`)

**Key Classes:**

#### `UDPProtocol(asyncio.DatagramProtocol)`
- Handles incoming UDP packets asynchronously
- Parses JSON sensor data
- Delegates to `RobotServer._handle_sensor_data()`

#### `RobotServer`
**Initialization:**
```python
def __init__(self, host: str, tcp_port: int, udp_port: int):
    self._tcp_server: asyncio.AbstractServer  # TCP listener
    self._udp_transport: asyncio.DatagramTransport  # UDP socket
    self._clients: dict[tuple, tuple[writer, parser, bot_type]]
    self._sensor_data: dict[tuple, dict]  # Latest sensor readings
    self._sensor_timestamps: dict[tuple, float]  # Freshness tracking
```

**Main Methods:**
- `start()`: Launches TCP server (port 3000) and UDP endpoint (port 3001)
- `_handle_client()`: Per-client TCP connection handler
  - Reads registration message
  - Assigns appropriate parser (R1D4 vs HOVERBOT)
  - Listens for incoming data
- `parse_and_send_to()`: Converts human command → robot JSON
- `_handle_sensor_data()`: Stores UDP sensor packets with timestamps
- `_stdin_router()`: Interactive CLI for manual control

**Registration Detection:**
```python
# Prefers JSON: {"command":"register","bot":"HOVERBOT"}
# Fallback 1: {"identity":"HOVERBOT"}
# Fallback 2: Text match "hoverbot" in message
```

---

### 2. Command Parsers (`src/llm/command_parser.py`)

#### `R1D4CommandParser`
**Input Format:** `"move 2.5"` or `"turn 90"`

**Output:**
```json
[{"command":"move", "float_data":[2.5]}]
[{"command":"turn", "float_data":[90.0]}]
```

**Use Case:** Simple 2-wheeled differential drive robots

---

#### `HOVERBOTCommandParser`
**Input Format:** `"forward 2.5"`, `"backward 1.0"`, `"ping lidar"`

**Output:**
```json
{
  "command": "FORWARD",
  "floatData": [2500.0],  // Converted to milliseconds
  "intData": [],
  "status": "DISPATCHED",
  "result": 0.0,
  "text": ""
}
```

**Command Mapping:**
```python
"forward"  → "FORWARD"   (meters → milliseconds conversion)
"backward" → "BACKWARD"
"left"     → "LEFT"      (strafe)
"right"    → "RIGHT"     (strafe)
"ping lidar" → "PINGLIDAR"
```

**Use Case:** Holonomic (omnidirectional) robots with advanced sensors

---

### 3. ESP32 Firmware (`main.c`)

#### Core Functions

**`app_main()`** - Entry point
1. Initialize NVS (non-volatile storage)
2. Configure UART for serial debugging
3. Check for `UART_MAGIC_TOOL` config commands
4. Load WiFi credentials from NVS
5. Start WiFi scan → triggers `event_handler()`

**`event_handler()`** - WiFi state machine
- `WIFI_EVENT_STA_START` → `esp_wifi_connect()`
- `WIFI_EVENT_STA_DISCONNECTED` → auto-reconnect
- `IP_EVENT_STA_GOT_IP` → launch `tcp_client()`

**`tcp_client()`** - Main command receiver (runs on Core 1)
1. Create TCP socket → `g_server_host:g_server_port`
2. Send registration: `"HOVERBOT\n"`
3. Create UDP socket for sensor streaming
4. Spawn `udp_sensor_stream_task()` on Core 0
5. Enter receive loop:
   - `recv()` JSON command
   - Parse with `cJSON`
   - Execute motor action
   - Send JSON response

**`udp_sensor_stream_task()`** - Sensor publisher (Core 0)
- Runs at 10 Hz (100ms interval)
- Calls `us_ping()` to get ultrasonic distance
- Builds JSON: `{"type":"proximity","timestamp":...,"distance_cm":...}`
- `sendto()` server UDP:3001

**Motor Control Functions:**
```c
void move_forward(int duration_ms) {
    gpio_set_level(LEFT_MOTOR_DIR_PIN, DIR_FORWARD);
    gpio_set_level(RIGHT_MOTOR_DIR_PIN, DIR_FORWARD);
    gpio_set_level(LEFT_MOTOR_STOP_PIN, STOP_DISEN);
    gpio_set_level(RIGHT_MOTOR_STOP_PIN, STOP_DISEN);
    vTaskDelay(pdMS_TO_TICKS(duration_ms));
    gpio_set_level(LEFT_MOTOR_STOP_PIN, STOP_ENGAGE);
    gpio_set_level(RIGHT_MOTOR_STOP_PIN, STOP_ENGAGE);
}
```

**Configuration via UART:**
```
UART_MAGIC_TOOL; set ssid MyWiFi
UART_MAGIC_TOOL; set pwd password123
UART_MAGIC_TOOL; set server_host 192.168.1.100
UART_MAGIC_TOOL; set server_port 3000
UART_MAGIC_TOOL; set identity HOVERBOT
```

---

## Protocol Specifications

### TCP Command Protocol (Port 3000)

**Direction:** Server → ESP32

**Format:** Newline-delimited JSON

**R1D4 Format:**
```json
[
  {"command": "move", "float_data": [2.5]},
  {"command": "turn", "float_data": [90.0]}
]
```

**HOVERBOT Format:**
```json
{
  "command": "FORWARD",
  "floatData": [2500.0],
  "intData": [],
  "status": "DISPATCHED",
  "result": 0.0,
  "text": ""
}
```

**ESP32 Response:**
```json
{
  "id": 0,
  "command": "FORWARD",
  "status": "SUCCESS",  // or "FAILURE"
  "intData": [],
  "floatData": [],
  "result": 2500.0,
  "text": "Optional message"
}
```

---

### UDP Sensor Protocol (Port 3001)

**Direction:** ESP32 → Server (one-way)

**Format:** JSON datagrams (fire-and-forget)

**Proximity Sensor:**
```json
{
  "type": "proximity",
  "timestamp": 1234.567,
  "distance_cm": 42,
  "robot_id": "HOVERBOT"
}
```

**Example Client Formats:**

**IMU:**
```json
{
  "type": "imu",
  "timestamp": 1234.567,
  "accel": {"x": 0.1, "y": 0.0, "z": 9.8},
  "gyro": {"x": 0.0, "y": 0.0, "z": 0.0}
}
```

**LIDAR:**
```json
{
  "type": "lidar",
  "timestamp": 1234.567,
  "distances": [0.5, 0.6, ...],  // 360 points
  "scan_rate": 10
}
```

---

## Setup & Deployment

### Prerequisites

**Server (macOS):**
- Python 3.10+
- espeak-ng (for TTS)
- OpenAI API key (optional, for voice)

**ESP32:**
- ESP-IDF v5.5.1
- USB serial adapter
- ESP32-WROVER-E board

---

### Quick Start

**1. Build & Flash ESP32:**
```bash
cd ~/capstone/swarm-server/hoverbot_external_code/SwarmBotESP/HoverBotESP
source $HOME/esp/v5.5.1/esp-idf/export.sh
./build.sh
idf.py -p /dev/tty.usbserial-140 flash monitor
```

**2. Start Server:**
```bash
cd ~/capstone/swarm-server
source .venv/bin/activate
python3 -m src.llm.server
```

**3. Test Connection:**
```
# Server terminal:
list              # Should show ESP32 IP
0                 # Select robot
forward 2.5       # Send command
sensors           # View UDP data
```

---

### Troubleshooting

**ESP32 won't connect:**
1. Check UART config: `idf.py monitor` → send `UART_MAGIC_TOOL; set ssid ...`
2. Verify server IP: `ifconfig | grep 172.20`
3. Check firewall: `sudo lsof -i :3000`

**No sensor data:**
- ESP32 must register as "HOVERBOT" (not R1D4)
- Check UDP port in `main.h`: `DEFAULT_UDP_PORT 3001`
- Enable debug: `idf.py -D DEBUG_MODE=1 flash monitor`

**Parser mismatch:**
- ESP32 sends `{"identity":"HOVERBOT"}` on registration
- Server logs should show `HOVERBOTCommandParser` (not R1D4)

---

## Advanced Features

### Voice Commands (Optional)
Requires `MANUAL_MODE = False` in `server.py` and `OPENAI_API_KEY` in `.env`:
```
"Move forward 2 meters and turn right"
→ [{"command":"move","float_data":[2.0]}, {"command":"turn","float_data":[90.0]}]
```

### Navigation System
`src/map/mapStructure.py` provides graph-based pathfinding:
```python
handle_navigation_command("kitchen", "bedroom")
→ [{"command":"turn","float_data":[90]}, {"command":"move","float_data":[5.0]}]
```

### Multi-Robot Coordination
Server tracks multiple clients in `_clients` dict. Use broadcast:
```
all              # Broadcast mode
forward 1.0      # All robots execute
```

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| TCP Latency | 5-50ms |
| UDP Throughput | 10 packets/sec/robot |
| Max Robots | Limited by network bandwidth |
| Command Queue | None (immediate execution) |
| Sensor Freshness | <1 second (configurable) |

---

## Security Considerations

⚠️ **Current Implementation:**
- No authentication
- Unencrypted TCP/UDP
- No command validation beyond parsing

🔒 **Production Recommendations:**
- Add TLS for TCP
- Implement DTLS for UDP
- Add robot authentication tokens
- Rate limit commands
- Validate command parameters (safety bounds)

---

## Future Enhancements

- [ ] WebSocket support for browser clients
- [ ] SLAM integration (map building)
- [ ] Swarm coordination algorithms
- [ ] Battery monitoring
- [ ] OTA firmware updates
- [ ] Web dashboard for monitoring
- [ ] Command queueing with priorities

---

## References

- ESP-IDF Documentation: https://docs.espressif.com/projects/esp-idf/
- Python asyncio: https://docs.python.org/3/library/asyncio.html
- cJSON Library: https://github.com/DaveGamble/cJSON
- FreeRTOS: https://www.freertos.org/
