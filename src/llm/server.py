
import json
import socket
import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from src.map.mapStructure import handle_navigation_command
from src.llm.command_parser import RobotCommandParser, R1D4CommandParser, get_parser
from src.llm.voice_command_interpreter import interpretSeriesOfCommands


# Server Configuration
HOST = "0.0.0.0"  # Listen on all network interfaces
PORT = int(os.environ.get("SERVER_PORT", 3000))  # Must match ESP32 port

# Enable or disable debug mode
DEBUG_MODE = False
MANUAL_MODE = True  # manual mode skips heavy STT/TTS initialization

if not MANUAL_MODE:
    from src.llm.stt.transcribe import FasterWhisper
    from src.llm.tts.text_to_speech import TextToSpeech
    TTS = TextToSpeech()
    STT = FasterWhisper()
else:
    class _NoOpTTS:
        def speak(self, text: str):
            pass
    class _NoOpSTT:
        def listen_transcribe(self) -> str:
            return ""
    TTS = _NoOpTTS()
    STT = _NoOpSTT()

async def a_tts_speak(text: str):
    await asyncio.to_thread(TTS.speak, text)

async def a_stt_listen_transcribe() -> str:
    return await asyncio.to_thread(STT.listen_transcribe)

async def a_input(prompt: str) -> str:
    # safe wrapper for blocking input()
    return await asyncio.to_thread(lambda: input(prompt))

async def listen_for_activation() -> bool:
    print("🎤 Waiting for 'listen' activation...")
    while True:
        try:
            command = (await a_stt_listen_transcribe()) or ""
            lc = command.lower()
            if "stop listening" in lc:
                print("🔇 Stopping activation loop.")
                return False
            if "listen" in lc:
                return True
        except Exception as e:
            print(f"❌ STT error: {e}")
            await asyncio.sleep(0.2)

async def capture_voice() -> str | None:
    try:
        msg = "What do you need me to do?"
        print(f"🎤 {msg}")
        await a_tts_speak(msg)
        return await a_stt_listen_transcribe()
    except Exception as e:
        print(f"❌ Capture error: {e}")
        return None

def _build_response_from_text_or_nav(voice_command: str | None) -> str:
    try:
        response_str = interpretSeriesOfCommands(voice_command) if voice_command else json.dumps([])
        print(f"🔍 Raw AI Response: {response_str}")

        if response_str and response_str.startswith("("):
            stripped = response_str.strip("()")
            parts = stripped.split(",")
            if len(parts) == 2:
                start_room = parts[0].strip()
                end_room = parts[1].strip()
                print(f"📍 Navigation from {start_room} to {end_room}")
                response_json = handle_navigation_command(start_room, end_room)

                if isinstance(response_json, str) and response_json.startswith("{"):
                    try:
                        response_data = json.loads(response_json)
                        if "error" in response_data:
                            return json.dumps([])
                    except Exception:
                        pass

                try:
                    nav_list = json.loads(response_json)
                    print("🧭 Navigation Commands:")
                    for c in nav_list:
                        print(c)
                    return json.dumps(nav_list)
                except Exception:
                    return json.dumps([])
            else:
                print("❌ Invalid navigation tuple format.")
                return json.dumps([])
        else:
            return response_str or json.dumps([])
    except Exception as e:
        print(f"❌ Build response error: {e}")
        return json.dumps([])

class RobotServer:
    """
    Async TCP server:
      - Accepts multiple robot connections.
      - Runs a single stdin router task to send manual commands to chosen client(s).
      - Provides broadcast() and send_to().
    Protocol: newline-delimited UTF-8 messages.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None
        self._clients: dict[tuple, tuple[asyncio.StreamWriter, RobotCommandParser, str]] = {}  # peername -> (writer, parser, bot_type)
        self._lock = asyncio.Lock()
        self._stdin_task: asyncio.Task | None = None

    async def start(self):
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        sockets = ", ".join(str(s.getsockname()) for s in (self._server.sockets or []))
        print(f"🚀 Server running on {sockets}")

        # Launch the single stdin router (manual command dispatcher)
        self._stdin_task = asyncio.create_task(self._stdin_router())
        print("🧭 Command router ready (type 'help' for options).")

    async def serve_forever(self):
        if not self._server:
            raise RuntimeError("Call start() first")
        async with self._server:
            await self._server.serve_forever()

    async def stop(self):
        # Stop router task first
        if self._stdin_task and not self._stdin_task.done():
            self._stdin_task.cancel()
            try:
                await self._stdin_task
            except asyncio.CancelledError:
                pass
            self._stdin_task = None

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        async with self._lock:
            for w in list(self._clients.values()):
                try:
                    w.close()
                except Exception:
                    pass
            self._clients.clear()

    async def parse_and_broadcast(self, raw_message: str):
        async with self._lock:
            items = list(self._clients.items())  # [(peer, (writer, parser, bot_type)), ...]
        
        out: list[tuple[asyncio.StreamWriter, bytes]] = []
        for peer, (writer, parser, bot_type) in items:
            try:
                payload = parser.parse_command(raw_message)
                if isinstance(payload, bytes):
                    data = payload
                else:
                    if not payload.endswith("\n"):
                        payload += "\n"
                    data = payload.encode("utf-8", errors="replace")
                out.append((writer, data))
            except Exception as e:
                print(f"❌ parse failed for {peer}: {e}")

        # write (transport stays dumb)
        for writer, data in out:
            try:
                writer.write(data)
            except Exception as e:
                print(f"❌ write failed: {e}")

        await asyncio.gather(*(w.drain() for w, _ in out), return_exceptions=True)

    async def parse_and_send_to(self, peername: tuple, raw_message: str):
        async with self._lock:
            sess = self._clients.get(peername)
        if not sess:
            print("❌ Unknown peer")
            return
        writer, parser, bot_type = sess
        payload = parser.parse_command(raw_message)  # -> str (or bytes; if bytes, handle below)
        if isinstance(payload, bytes):
            data = payload
        else:
            if not payload.endswith("\n"):
                payload += "\n"
            data = payload.encode("utf-8", errors="replace")
        try:
            writer.write(data)
            await writer.drain()
        except Exception as e:
            print(f"❌ write failed: {e}")

    async def connected_peers(self) -> list[tuple]:
        async with self._lock:
            return list(self._clients.keys())

    async def _write_to_writers(self, peernames, message: str):
        if not message.endswith("\n"):
            message += "\n"
        data = message.encode("utf-8", errors="replace")
        async with self._lock:
            tuples = [self._clients.get(p) for p in peernames if p in self._clients]
            writers = [t[0] for t in tuples]
            parsers = [t[1] for t in tuples]
        for w, p in zip(writers, parsers):
            if not w:
                continue
            try:
                w.write(data)
            except Exception as e:
                print(f"❌ write failed: {e}")
        await asyncio.gather(*(w.drain() for w in writers if w), return_exceptions=True)

    # ---------- Per-client handler ----------

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername")  # (ip, port)
        print(f"✅ Connection from {peer}")

        async with self._lock:
            self._clients[peer] = (writer, R1D4CommandParser(), "R1D4")

        try:
            if MANUAL_MODE:
                # In manual mode, per-client handler does NOT read stdin.
                # It just keeps the connection open and optionally logs client messages.
                while True:
                    data = await reader.readline()
                    if not data:
                        break
                    msg = data.decode("utf-8", errors="replace").rstrip()
                    if msg:
                        print(f"📥 From {peer}: {msg}")
                        registered = False
                        if msg.startswith("{"):
                            try:
                                json_msg = json.loads(msg)
                            except Exception:
                                json_msg = None
                            if isinstance(json_msg, dict):
                                # Preferred explicit registration message
                                if json_msg.get("command") == "register" and json_msg.get("bot"):
                                    bot_type = json_msg.get("bot")
                                    try:
                                        parser = get_parser(bot_type)
                                    except Exception:
                                        parser = R1D4CommandParser(); bot_type = "R1D4"
                                    print(f"✅ [REGISTRATION] Client {peer} registered as {bot_type}")
                                    print(f"   Parser type: {type(parser).__name__}")
                                    async with self._lock:
                                        self._clients[peer] = (writer, parser, bot_type)
                                    parser.list_available_commands()
                                    registered = True
                                # Fallback: identity field
                                elif not registered and json_msg.get("identity"):
                                    bot_type = json_msg.get("identity")
                                    try:
                                        parser = get_parser(bot_type)
                                    except Exception:
                                        parser = R1D4CommandParser(); bot_type = "R1D4"
                                    print(f"✅ [REGISTRATION/IDENTITY] Client {peer} registered as {bot_type}")
                                    print(f"   Parser type: {type(parser).__name__}")
                                    async with self._lock:
                                        self._clients[peer] = (writer, parser, bot_type)
                                    parser.list_available_commands()
                                    registered = True
                        # Text fallback
                        if not registered:
                            lower = msg.lower()
                            if "hoverbot" in lower and ("register" in lower or lower.strip()=="hoverbot"):
                                bot_type = "HOVERBOT"
                                try:
                                    parser = get_parser(bot_type)
                                except Exception:
                                    parser = R1D4CommandParser(); bot_type = "R1D4"
                                print(f"✅ [REGISTRATION/FALLBACK] Client {peer} registered as {bot_type}")
                                print(f"   Parser type: {type(parser).__name__}")
                                async with self._lock:
                                    self._clients[peer] = (writer, parser, bot_type)
                                parser.list_available_commands()
            else:
                # Voice-activated flow (per client)
                while True:
                    activated = await listen_for_activation()
                    if not activated:
                        break
                    voice_command = await capture_voice()
                    response_json = _build_response_from_text_or_nav(voice_command)

                    try:
                        if response_json and response_json != "[]":
                            await a_tts_speak("Executing command.")
                        else:
                            await a_tts_speak("I didn't quite understand.")
                    except Exception as e:
                        print(f"❌ TTS speak failed: {e}")

                    await self._send_json(writer, response_json)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ Handler error for {peer}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            async with self._lock:
                self._clients.pop(peer, None)
            print(f"🔌 Client disconnected: {peer}")

    async def _send_json(self, writer: asyncio.StreamWriter, json_str: str):
        if not json_str.endswith("\n"):
            json_str += "\n"
        writer.write(json_str.encode("utf-8", errors="replace"))
        await writer.drain()

    # ---------- Single stdin router (manual dispatcher) ----------

    async def _stdin_router(self):
        """
        Runs once for the whole server. Lets the operator:
          - 'list'     -> list connected clients
          - 'all'      -> send next ManualControl command to all clients
          - '<index>'  -> send next ManualControl command to a single client
          - 'help'     -> show help
          - 'quit'     -> stop server
        The payload is produced by ManualControl.get_command_message() (unchanged).
        """
        await a_tts_speak("Manual control enabled.")
        while True:
            try:
                cmd = (await a_input("\nTarget (list | all | <index> | help | quit): ")).strip().lower()

                if cmd == "help":
                    print("Commands:\n  list      - show connected clients\n  all       - broadcast next manual command\n  <index>   - send to indexed client\n  quit      - stop server")
                elif cmd == "list":
                    await self._print_client_list()
                elif cmd == "quit":
                    print("🛑 Shutting down...")
                    # stop() will cancel this task from outside main()
                    asyncio.get_running_loop().call_soon(asyncio.create_task, self.stop())
                    return
                elif cmd != "all":
                    # None of the above -> expects an integer index 
                    try:
                        idx = int(cmd)
                    except ValueError:
                        print("❌ Unknown command. Type 'help' or 'list'.")
                        continue
                    peers = await self.connected_peers()
                    if idx < 0 or idx >= len(peers):
                        print("❌ Invalid index.")
                        continue
                    target = peers[idx]
                    writer, parser, bot_type = self._clients.get(target)
                    print(f"\n🤖 Selected: {bot_type} at {target}")
                    parser.list_available_commands()
                    raw_message = await a_input(f"\nEnter command for {target}: ")
                    await self.parse_and_send_to(target, raw_message)
                    print(f"📤 Sending to {target}: {raw_message}")
                    await a_tts_speak("Executing manual command.")
                elif cmd == "all":
                    raw_message = await a_input("\nEnter command to broadcast to all: ")
                    await self.parse_and_broadcast(raw_message)
                    await a_tts_speak("Broadcasting manual command.")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Router error: {e}")
                await asyncio.sleep(0.2)

    async def _print_client_list(self):
        peers = await self.connected_peers()
        if not peers:
            print("No clients connected.")
            return
        print("Connected clients:")
        async with self._lock:
            for i, p in enumerate(peers):
                writer, parser, bot_type = self._clients.get(p, (None, None, "Unknown"))
                parser_name = type(parser).__name__ if parser else "None"
                print(f"  [{i}] {p[0]}:{p[1]} - {bot_type} ({parser_name})")

async def main():
    server = RobotServer(HOST, PORT)
    await server.start()
    try:
        await server.serve_forever()
    finally:
        await server.stop()

if __name__ == "__main__":
    print("Starting Robot Server...")
    asyncio.run(main())