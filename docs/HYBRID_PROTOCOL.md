# Hybrid TCP/UDP Protocol Documentation

## Overview

The server now implements a **hybrid communication architecture**:

- **TCP (Port 3000)**: Reliable command delivery
- **UDP (Port 3001)**: High-frequency sensor data streaming

---

## Protocol Details

### TCP - Command Channel

**Purpose**: Bidirectional reliable command/control communication

**Port**: 3000 (configurable via `SERVER_PORT` env var)

**Format**: Newline-delimited UTF-8 JSON messages

**Client Flow**:
1. Connect to server TCP port
2. Send registration message: `{"command":"register", "bot":"R1D4"}` or `{"command":"register", "bot":"HOVERBOT"}`
3. Receive commands from server
4. Send acknowledgments/status updates back

**Example Commands** (Server → Robot):
```json
[{"command":"move", "float_data":[1.5]}]
[{"command":"turn", "float_data":[90.0]}]
```

**Example Registration** (Robot → Server):
```json
{"command":"register", "bot":"HOVERBOT"}
```

---

### UDP - Sensor Data Channel

**Purpose**: One-way high-frequency sensor telemetry

**Port**: 3001 (configurable via `UDP_PORT` env var)

**Format**: JSON-encoded sensor packets

**Client Flow**:
1. Send sensor data packets to server UDP port
2. No acknowledgment expected (fire-and-forget)
3. Recommended rate: 10-50 Hz depending on sensor type

**Sensor Data Format**:
```json
{
  "type": "lidar",
  "timestamp": 1638360000.123,
  "distances": [0.5, 0.6, 0.4, ...],
  "angles": [0, 1, 2, ...]
}
```

```json
{
  "type": "imu",
  "timestamp": 1638360000.456,
  "accel": {"x": 0.1, "y": 0.0, "z": 9.8},
  "gyro": {"x": 0.0, "y": 0.0, "z": 0.0}
}
```

```json
{
  "type": "depth_camera",
  "timestamp": 1638360000.789,
  "width": 640,
  "height": 480,
  "data_url": "base64_encoded_or_reference"
}
```

---

## Server Commands

When running the server, use these commands:

- `list` - Show all connected TCP clients
- `sensors` - Display latest sensor data received via UDP
- `all` - Broadcast command to all robots
- `<index>` - Send command to specific robot (by index)
- `help` - Show available commands
- `quit` - Shutdown server

---

## Configuration

Create a `.env` file:
```bash
SERVER_PORT=3000      # TCP command port
UDP_PORT=3001         # UDP sensor port
OPENAI_API_KEY=sk-... # For voice command interpretation
```

---

## Advantages of Hybrid Approach

| Feature | TCP | UDP |
|---------|-----|-----|
| **Reliability** | ✅ Guaranteed delivery | ❌ Best effort |
| **Ordering** | ✅ In-order | ❌ May arrive out of order |
| **Latency** | ~5-50ms | ~1-10ms |
| **Overhead** | Higher (ACKs, retransmits) | Lower (no handshake) |
| **Use Case** | Commands, registration | Sensor streams, telemetry |
| **Connection** | Stateful | Stateless |

**Best Practices**:
- Use TCP for: movement commands, configuration, critical status
- Use UDP for: LIDAR scans, IMU data, camera frames, heartbeats
- If a sensor reading is critical, send via TCP instead
- Add timestamps to UDP packets to detect stale data

---

## Example Client Implementation

See `examples/hybrid_client.py` for a reference implementation.
