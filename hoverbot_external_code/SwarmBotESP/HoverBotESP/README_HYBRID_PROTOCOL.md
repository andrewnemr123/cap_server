# ESP32 HoverBot - Hybrid TCP/UDP Protocol

## Overview

This ESP32 firmware implements a **hybrid TCP/UDP networking architecture** for robot control and sensor streaming:

- **TCP (Port 3000)**: Reliable command reception and acknowledgment
- **UDP (Port 3001)**: High-frequency sensor data streaming (10 Hz)

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Python Server                      │
│  ┌──────────────┐        ┌──────────────┐      │
│  │  TCP Server  │        │  UDP Server  │      │
│  │  Port 3000   │        │  Port 3001   │      │
│  └──────┬───────┘        └──────┬───────┘      │
└─────────┼────────────────────────┼──────────────┘
          │                        │
          │ Commands               │ Sensor Data
          │ (JSON)                 │ (JSON)
          │                        │
┌─────────┼────────────────────────┼──────────────┐
│         ▼                        ▼              │
│  ┌──────────────┐        ┌──────────────┐      │
│  │  TCP Client  │        │  UDP Client  │      │
│  │    (Main)    │        │   (Task)     │      │
│  └──────┬───────┘        └──────┬───────┘      │
│         │                        │              │
│         │ Commands               │ Reads        │
│         ▼                        ▼              │
│  ┌──────────────────────────────────────┐      │
│  │        Motor Driver                  │      │
│  │   (GPIO control + ultrasonic)        │      │
│  └──────────────────────────────────────┘      │
│               ESP32 HoverBot                    │
└─────────────────────────────────────────────────┘
```

## Communication Protocols

### TCP - Commands (Port 3000)

**Server → Robot (Command)**
```json
{
  "id": 1,
  "command": "FORWARD",
  "status": "DISPATCHED",
  "intData": [],
  "floatData": [2000.0],
  "result": 0.0,
  "text": ""
}
```

**Robot → Server (Response)**
```json
{
  "id": 1,
  "command": "FORWARD",
  "status": "SUCCESS",
  "intData": [],
  "floatData": [],
  "result": 2000.0,
  "text": ""
}
```

**Supported Commands:**
- `FORWARD` - Move forward (duration_ms in floatData[0])
- `BACKWARD` - Move backward (duration_ms in floatData[0])
- `TURNLEFT` - Rotate left (duration_ms in floatData[0])
- `TURNRIGHT` - Rotate right (duration_ms in floatData[0])
- `PING` - Ultrasonic distance measurement (returns distance_cm in result)

### UDP - Sensor Data (Port 3001)

**Robot → Server (Periodic @ 10 Hz)**
```json
{
  "type": "proximity",
  "timestamp": 1638360123.456,
  "distance_cm": 42,
  "robot_id": "HOVERBOT"
}
```

**Sensor Types:**
- `proximity` - Ultrasonic distance sensor data

## Configuration

### WiFi & Server Settings

Settings are stored in NVS (non-volatile storage) and can be configured via UART:

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| `ssid` | `AndrewiPhone` | WiFi SSID |
| `pwd` | `andypass` | WiFi Password |
| `server_host` | `172.20.10.2` | Server IP address |
| `server_port` | `3000` | TCP command port |
| `identity` | `HOVERBOT` | Robot identifier |

### UART Configuration Tool

Connect via serial terminal (115200 baud) and send:

```
UART_MAGIC_TOOL;set ssid YourNetwork
UART_MAGIC_TOOL;set pwd YourPassword
UART_MAGIC_TOOL;set server_host 192.168.1.100
UART_MAGIC_TOOL;set server_port 3000
UART_MAGIC_TOOL;set identity ROBOT_001
UART_MAGIC_TOOL;done configuration
```

To reset to defaults:
```
UART_MAGIC_TOOL;reset
```

## Implementation Details

### FreeRTOS Task Architecture

1. **Main Task (Core 1)**: TCP client
   - Connects to server
   - Receives commands
   - Executes motor actions
   - Sends JSON responses

2. **UDP Sensor Task (Core 0)**: Sensor streaming
   - Samples ultrasonic sensor @ 10 Hz
   - Builds JSON sensor packets
   - Sends UDP datagrams
   - Runs independently (non-blocking)

### Key Design Features

**Parallel Execution**
- TCP and UDP operate on separate cores (ESP32 dual-core)
- Motor commands execute synchronously on TCP task
- Sensor reads happen asynchronously on UDP task

**Error Handling**
- UDP socket failure doesn't prevent TCP operation
- Missing sensor data doesn't block command execution
- Auto-reconnect on WiFi disconnect

**Memory Management**
- Dynamic JSON creation/deletion with cJSON
- Heap-allocated task parameters
- Proper cleanup on socket close

## Usage Example

### Python Server Interaction

```python
import asyncio
import socket

# TCP: Send command
tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_sock.connect(("172.20.10.2", 3000))
tcp_sock.sendall(b'{"command":"FORWARD","floatData":[2000.0]}')
response = tcp_sock.recv(1024)
print(f"Response: {response.decode()}")

# UDP: Receive sensor data
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind(("0.0.0.0", 3001))
while True:
    data, addr = udp_sock.recvfrom(512)
    print(f"Sensor from {addr}: {data.decode()}")
```

### Testing on Server

With the hybrid Python server running:

```bash
# Terminal 1: Start server
python3 -m src.llm.server

# Terminal 2: Watch sensor data
# Type "sensors" in the server console

# Terminal 3: Send commands
# Type "list" to see robots
# Type "0" to select first robot
# Type "move 2.0" to send command
```

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| TCP Latency | ~50-100ms | Command round-trip time |
| UDP Rate | 10 Hz | Configurable (100ms interval) |
| UDP Packet Size | ~120 bytes | JSON sensor payload |
| WiFi Reconnect | Automatic | Event-driven handler |
| Core Usage | Dual-core | TCP on core 1, UDP on core 0 |

## Building & Flashing

```bash
# Configure project (first time only)
idf.py menuconfig

# Build firmware
idf.py build

# Flash to ESP32
idf.py -p /dev/tty.usbserial-140 flash

# Monitor serial output
idf.py -p /dev/tty.usbserial-140 monitor
```

## Troubleshooting

**UDP packets not appearing on server:**
- Verify DEFAULT_UDP_PORT matches server configuration (3001)
- Check firewall rules on server machine
- Use Wireshark to verify packet transmission
- Confirm `udp_sensor_stream_task` started (check logs)

**High UDP packet loss:**
- Increase task interval (reduce frequency)
- Check WiFi signal strength
- Reduce JSON payload size
- Verify network congestion

**TCP disconnects frequently:**
- Verify stable WiFi connection
- Check server timeout settings
- Monitor ESP32 heap memory (potential leak)
- Increase TCP socket buffer if needed

## Future Enhancements

- [ ] Add IMU data streaming (accelerometer/gyroscope)
- [ ] Implement camera frame streaming over UDP
- [ ] Add sensor data compression (MessagePack/CBOR)
- [ ] Implement UDP packet acknowledgment for critical sensors
- [ ] Add adaptive sampling rate based on network conditions
- [ ] Multi-sensor fusion in single UDP packet

## License

Part of the SwarmBot capstone project.
