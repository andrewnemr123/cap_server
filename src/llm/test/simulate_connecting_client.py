import asyncio

HOST = "127.0.0.1"  # server IP (or your LAN IP for ESP32)
PORT = 3000         # must match SERVER_PORT

async def handle_server(reader: asyncio.StreamReader):
    """Continuously read and print messages from the server."""
    while True:
        data = await reader.readline()
        if not data:
            print("🔌 Server closed connection.")
            break
        message = data.decode("utf-8", errors="replace").rstrip()
        print(f"📥 Received: {message}")

async def client_main():
    print(f"🔗 Connecting to {HOST}:{PORT} ...")
    reader, writer = await asyncio.open_connection(HOST, PORT)
    peername = writer.get_extra_info("sockname")
    print(f"✅ Connected as {peername}")

    # Task to continuously read server responses
    asyncio.create_task(handle_server(reader))

    # Example: periodically send heartbeat or dummy messages
    try:
        while True:
            await asyncio.sleep(3)
    except KeyboardInterrupt:
        print("🛑 Disconnecting...")
    finally:
        writer.close()
        await writer.wait_closed()

if __name__ == "__main__":
    asyncio.run(client_main())
