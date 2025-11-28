import asyncio
import json
import os
import sys

HOST = os.environ.get("SERVER_HOST", "127.0.0.1")  # override with env if needed
PORT = int(os.environ.get("SERVER_PORT", 3000))     # must match server

REGISTER_PAYLOAD = {"command": "register", "bot": "HOVERBOT"}
HEARTBEAT_INTERVAL_SEC = 10

async def handle_server(reader: asyncio.StreamReader):
    """Continuously read and print messages from the server."""
    while True:
        data = await reader.readline()
        if not data:
            print("🔌 Server closed connection.")
            break
        message = data.decode("utf-8", errors="replace").rstrip()
        print(f"📥 Received: {message}")

async def _send_registration(writer: asyncio.StreamWriter):
    line = json.dumps(REGISTER_PAYLOAD) + "\n"
    writer.write(line.encode("utf-8"))
    await writer.drain()
    print("📤 Sent registration:", line.strip())

async def _heartbeat_loop(writer: asyncio.StreamWriter):
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
        # optional: send a lightweight ping; server currently ignores unparsed lines
        ping_line = "{\"command\":\"ping\"}\n"
        try:
            writer.write(ping_line.encode("utf-8"))
            await writer.drain()
            print("📤 Heartbeat ping sent")
        except Exception as e:
            print("❌ Heartbeat failed:", e)
            return

async def _manual_input_loop(writer: asyncio.StreamWriter):
    """Optional manual command injection (press Enter after typing)."""
    loop = asyncio.get_running_loop()
    while True:
        try:
            raw = await loop.run_in_executor(None, sys.stdin.readline)
            if not raw:
                continue
            raw = raw.strip()
            if raw.lower() in {"exit", "quit"}:
                print("🚪 Exit requested.")
                break
            # Send raw line; server will try to parse if matches expected syntax
            writer.write((raw + "\n").encode("utf-8"))
            await writer.drain()
            print("📤 Sent manual line:", raw)
        except Exception as e:
            print("❌ Manual input error:", e)
            break

async def client_main():
    print(f"🔗 Connecting to {HOST}:{PORT} ...")
    reader, writer = await asyncio.open_connection(HOST, PORT)
    peername = writer.get_extra_info("sockname")
    print(f"✅ Connected as {peername}")

    # Start server read task
    asyncio.create_task(handle_server(reader))

    # Register as Hoverbot immediately
    await _send_registration(writer)

    # Start heartbeat & manual input tasks
    asyncio.create_task(_heartbeat_loop(writer))
    asyncio.create_task(_manual_input_loop(writer))

    try:
        while True:
            await asyncio.sleep(3600)  # keep process alive
    except KeyboardInterrupt:
        print("🛑 Disconnecting...")
    finally:
        writer.close()
        await writer.wait_closed()

if __name__ == "__main__":
    asyncio.run(client_main())
