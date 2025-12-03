"""
Hoverbot LIDAR UDP Test Client

Simulates a Hoverbot sending LIDAR data via UDP to the server.
Also maintains TCP connection for commands.
"""

import asyncio
import json
import os
import re
import time
from typing import List

# Configuration
SERVER_HOST = os.environ.get("SERVER_HOST", "172.20.10.2")  # Server laptop IP
TCP_PORT = int(os.environ.get("SERVER_PORT", 3000))
UDP_PORT = int(os.environ.get("UDP_PORT", 3001))
LIDAR_FILE = "test_data/LIDAR_message.txt"
SEND_INTERVAL = 0.1  # seconds between UDP packets


def parse_lidar_file(filepath: str) -> list[dict]:
    """Parse LIDAR test data file into scan points."""
    scans = []
    with open(filepath, 'r') as f:
        for line in f:
            # Parse: "18701: Angle:119.265625, Distance:2811.5"
            match = re.match(r'(\d+):\s*Angle:([\d.]+),\s*Distance:([\d.]+)', line.strip())
            if match:
                scan_id, angle, distance = match.groups()
                scans.append({
                    "id": int(scan_id),
                    "angle": float(angle),
                    "distance": float(distance)
                })
    return scans


async def tcp_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, ping_queue: asyncio.Queue):
    """Handle incoming TCP commands from server."""
    peer = writer.get_extra_info("peername")
    print(f"📥 TCP: Connected to server {peer}")
    
    # Send registration
    reg_msg = json.dumps({"command": "register", "bot": "HOVERBOT"}) + "\n"
    writer.write(reg_msg.encode("utf-8"))
    await writer.drain()
    print("✅ Sent registration")
    
    try:
        while True:
            data = await reader.readline()
            if not data:
                print("🔌 Server closed TCP connection")
                break
            msg = data.decode("utf-8", errors="replace").rstrip()
            print(f"📥 TCP Command: {msg}")
            
            # Parse and simulate command execution
            try:
                cmd = json.loads(msg)
                command_name = cmd.get("command", "").upper()
                float_data = cmd.get("floatData", [])
                
                if command_name in ["FORWARD", "BACKWARD", "LEFT", "RIGHT"]:
                    distance = float_data[0] if float_data else 0
                    print(f"  🤖 Simulating {command_name} {distance}m")
                elif command_name in ("PINGLIDAR", "PING"):
                    print(f"  📡 Received {command_name} -> sending full LIDAR dataset once")
                    # enqueue a ping token; UDP task will send full dataset once
                    try:
                        ping_queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass
                elif command_name == "PING3DCAMERA":
                    print(f"  📷 Simulating 3D camera ping")
                else:
                    print(f"  ⚠️  Unknown command: {command_name}")
            except json.JSONDecodeError:
                print(f"  ⚠️  Non-JSON command: {msg}")
    except Exception as e:
        print(f"❌ TCP handler error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def udp_sender(scans: List[dict], ping_queue: asyncio.Queue):
    """Wait for ping, then send entire LIDAR dataset in batches of 10 via UDP."""
    loop = asyncio.get_running_loop()
    
    # Create UDP socket
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: asyncio.DatagramProtocol(),
        remote_addr=(SERVER_HOST, UDP_PORT)
    )
    
    print(f"📡 UDP: Ready to send to {SERVER_HOST}:{UDP_PORT} (waiting for ping)")
    
    try:
        while True:
            # Await a ping trigger
            await ping_queue.get()
            total = len(scans)
            if total == 0:
                print("⚠️ No scans loaded, skipping send.")
                continue
            print(f"🚀 Sending {total} scans in batches of 10 (one-time for this ping)")

            batch_size = 1000
            sent = 0
            for scan_idx in range(0, total, batch_size):
                batch = scans[scan_idx:scan_idx + batch_size]
                packet = {
                    "type": "lidar",
                    "timestamp": time.time(),
                    "scans": batch
                }
                message = json.dumps(packet).encode("utf-8")
                transport.sendto(message)
                sent += len(batch)
                print(f"📤 Sent {len(batch)} scans (angles {batch[0]['angle']:.1f}-{batch[-1]['angle']:.1f}°) [{sent}/{total}]")
                await asyncio.sleep(SEND_INTERVAL)
            print("✅ Finished sending dataset for this ping. Waiting for next ping...")
            
    except Exception as e:
        print(f"❌ UDP sender error: {e}")
    finally:
        transport.close()


async def main():
    print("🤖 Hoverbot LIDAR Simulator")
    print(f"   Server: {SERVER_HOST}")
    print(f"   TCP Port: {TCP_PORT}")
    print(f"   UDP Port: {UDP_PORT}")
    print()
    
    # Load LIDAR data
    try:
        scans = parse_lidar_file(LIDAR_FILE)
        print(f"✅ Loaded {len(scans)} LIDAR scans from {LIDAR_FILE}")
    except Exception as e:
        print(f"❌ Failed to load LIDAR data: {e}")
        return
    
    # Connect TCP for commands
    try:
        reader, writer = await asyncio.open_connection(SERVER_HOST, TCP_PORT)
    except Exception as e:
        print(f"❌ TCP connection failed: {e}")
        return
    
    # Coordination queue for ping triggers
    ping_queue: asyncio.Queue = asyncio.Queue(maxsize=5)

    # Run TCP handler and UDP sender concurrently
    tcp_task = asyncio.create_task(tcp_handler(reader, writer, ping_queue))
    udp_task = asyncio.create_task(udp_sender(scans, ping_queue))
    
    try:
        await asyncio.gather(tcp_task, udp_task)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        tcp_task.cancel()
        udp_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
