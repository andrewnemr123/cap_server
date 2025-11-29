"""
Example hybrid TCP/UDP client for robot communication.

TCP: Send/receive commands
UDP: Stream sensor data to server
"""

import asyncio
import json
import time
import random
from typing import Optional

SERVER_HOST = "127.0.0.1"
TCP_PORT = 3000
UDP_PORT = 3001

class HybridRobotClient:
    """Example robot client with TCP command channel and UDP sensor streaming."""
    
    def __init__(self, bot_type: str = "R1D4"):
        self.bot_type = bot_type
        self.tcp_reader: Optional[asyncio.StreamReader] = None
        self.tcp_writer: Optional[asyncio.StreamWriter] = None
        self.udp_transport: Optional[asyncio.DatagramTransport] = None
        self.running = False
    
    async def connect_tcp(self):
        """Connect to server's TCP command channel."""
        self.tcp_reader, self.tcp_writer = await asyncio.open_connection(
            SERVER_HOST, TCP_PORT
        )
        print(f"✅ TCP connected to {SERVER_HOST}:{TCP_PORT}")
        
        # Send registration message
        registration = {"command": "register", "bot": self.bot_type}
        await self._send_tcp(registration)
        print(f"📝 Registered as {self.bot_type}")
    
    async def setup_udp(self):
        """Setup UDP socket for sensor data transmission."""
        loop = asyncio.get_running_loop()
        self.udp_transport, _ = await loop.create_datagram_endpoint(
            lambda: asyncio.DatagramProtocol(),
            remote_addr=(SERVER_HOST, UDP_PORT)
        )
        print(f"📡 UDP socket ready (target: {SERVER_HOST}:{UDP_PORT})")
    
    async def _send_tcp(self, data: dict):
        """Send JSON message over TCP."""
        if not self.tcp_writer:
            return
        message = json.dumps(data) + "\n"
        self.tcp_writer.write(message.encode('utf-8'))
        await self.tcp_writer.drain()
    
    def send_udp(self, data: dict):
        """Send JSON message over UDP."""
        if not self.udp_transport:
            return
        message = json.dumps(data).encode('utf-8')
        self.udp_transport.sendto(message)
    
    async def listen_for_commands(self):
        """Listen for commands from server over TCP."""
        print("👂 Listening for commands...")
        try:
            while self.running and self.tcp_reader:
                line = await self.tcp_reader.readline()
                if not line:
                    print("🔌 TCP connection closed by server")
                    break
                
                message = line.decode('utf-8', errors='replace').strip()
                if message:
                    await self._handle_command(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ TCP error: {e}")
    
    async def _handle_command(self, message: str):
        """Process received command."""
        try:
            commands = json.loads(message)
            print(f"\n📥 Received: {commands}")
            
            # Execute commands (simulation)
            if isinstance(commands, list):
                for cmd in commands:
                    await self._execute_command(cmd)
            else:
                await self._execute_command(commands)
        except json.JSONDecodeError:
            print(f"⚠️  Non-JSON message: {message}")
    
    async def _execute_command(self, cmd: dict):
        """Simulate command execution."""
        command_type = cmd.get('command', 'unknown')
        
        if command_type == 'move':
            distance = cmd.get('float_data', [0])[0]
            print(f"🚗 Moving {distance} meters...")
            await asyncio.sleep(abs(distance) * 0.5)  # Simulate movement time
            
        elif command_type == 'turn':
            angle = cmd.get('float_data', [0])[0]
            print(f"🔄 Turning {angle} degrees...")
            await asyncio.sleep(abs(angle) / 180)  # Simulate turn time
            
        else:
            print(f"❓ Unknown command: {command_type}")
        
        # Send acknowledgment via TCP
        ack = {"status": "completed", "command": command_type}
        await self._send_tcp(ack)
    
    async def stream_sensor_data(self):
        """Simulate streaming sensor data via UDP."""
        print("📊 Starting sensor data stream...")
        try:
            while self.running:
                # Simulate different sensor types
                sensor_type = random.choice(['lidar', 'imu', 'proximity'])
                
                if sensor_type == 'lidar':
                    data = {
                        "type": "lidar",
                        "timestamp": time.time(),
                        "distances": [random.uniform(0.1, 5.0) for _ in range(360)],
                        "scan_rate": 10
                    }
                elif sensor_type == 'imu':
                    data = {
                        "type": "imu",
                        "timestamp": time.time(),
                        "accel": {
                            "x": random.uniform(-1, 1),
                            "y": random.uniform(-1, 1),
                            "z": random.uniform(9, 10)
                        },
                        "gyro": {
                            "x": random.uniform(-0.1, 0.1),
                            "y": random.uniform(-0.1, 0.1),
                            "z": random.uniform(-0.1, 0.1)
                        }
                    }
                else:
                    data = {
                        "type": "proximity",
                        "timestamp": time.time(),
                        "front": random.uniform(0, 2),
                        "back": random.uniform(0, 2),
                        "left": random.uniform(0, 2),
                        "right": random.uniform(0, 2)
                    }
                
                self.send_udp(data)
                await asyncio.sleep(0.1)  # 10 Hz sensor rate
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ Sensor stream error: {e}")
    
    async def run(self):
        """Main client loop."""
        self.running = True
        
        try:
            # Connect to server
            await self.connect_tcp()
            await self.setup_udp()
            
            # Run command listener and sensor streamer concurrently
            await asyncio.gather(
                self.listen_for_commands(),
                self.stream_sensor_data()
            )
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Close connections."""
        self.running = False
        
        if self.tcp_writer:
            self.tcp_writer.close()
            await self.tcp_writer.wait_closed()
            print("🔌 TCP disconnected")
        
        if self.udp_transport:
            self.udp_transport.close()
            print("📡 UDP closed")

async def main():
    """Run example client."""
    print("🤖 Starting Hybrid Robot Client Example\n")
    
    client = HybridRobotClient(bot_type="R1D4")
    
    try:
        await client.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
