from abc import ABC, abstractmethod
import json

class RobotCommandParser(ABC):
    @staticmethod
    @abstractmethod
    def parse_command(command_str: str) -> str:
        """
        Parses a string and returns the associated command in a structured format.

        Throws an exception for invalid or misstructured commands based on specific parsing rules
        """
        pass
    
    @staticmethod
    @abstractmethod
    def list_available_commands():
        """Lists all available commands with descriptions, including aliases, usage, and examples"""
        pass

class R1D4CommandParser(RobotCommandParser):
    commands_docs = {
        "Move": {"aliases":["move", "m"], "description": "Move robot by specified meters", "usage": "move <meters:float>", "example": "move 1.0"},
        "Turn": {"aliases":["turn", "t"], "description": "Turn robot by specified degrees", "usage": "turn <degrees:float>", "example": "turn 90.0"}
    }
    
    @staticmethod
    def parse_command(command_str: str) -> str:
        if not command_str or not command_str.strip():
            raise ValueError("Empty command string")
        parts = command_str.strip().split()
        if len(parts) != 2:
            raise ValueError("Invalid input: requires exactly 2 arguments")

        verb = parts[0].lower()
        try:
            value = float(parts[1])
        except ValueError:
            raise ValueError("Invalid input: numeric value required")

        if verb in R1D4CommandParser.commands_docs["Move"]["aliases"]:
            # Convert meters to milliseconds (assuming 0.5 m/s speed)
            duration_ms = value * 2000.0
            msg = {
                "id": 1,
                "command": "move",
                "status": "DISPATCHED",
                "intData": [],
                "floatData": [duration_ms],
                "result": 0.0,
                "text": ""
            }
            return json.dumps(msg)
            
        if verb in R1D4CommandParser.commands_docs["Turn"]["aliases"]:
            msg = {
                "id": 1,
                "command": "turn",
                "status": "DISPATCHED",
                "intData": [],
                "floatData": [value],
                "result": 0.0,
                "text": ""
            }
            return json.dumps(msg)

        raise ValueError("Invalid input: unknown command")
    
    @staticmethod
    def list_available_commands():
        print("🧭 Manual Mode Active! Available Commands:")
        for command, doc in R1D4CommandParser.commands_docs.items():
            print(f"- {command}: {doc['description']}. Usage: {doc['usage']}")
        pass


class HOVERBOTCommandParser(RobotCommandParser):
    command_docs = {
        "Forward": {"aliases":["forward", "f"], "description": "Move robot forward by specified meters", "usage": "forward <meters:float>", "example": "forward 1.0"},
        "Backward": {"aliases":["backward", "b"], "description": "Move robot backward by specified meters", "usage": "backward <meters:float>", "example": "backward 1.0"},
        "Turn Left": {"aliases":["turnleft", "tl", "left"], "description": "Turn robot left by specified degrees", "usage": "turnleft <degrees:float>", "example": "turnleft 90"},
        "Turn Right": {"aliases":["turnright", "tr", "right"], "description": "Turn robot right by specified degrees", "usage": "turnright <degrees:float>", "example": "turnright 90"},
        "Ping": {"aliases":["ping", "p"], "description": "Ping the ultrasonic sensor", "usage": "ping", "example": "ping"},
    }
    
    @staticmethod
    def parse_command(command_str: str) -> str:
        if not command_str or not command_str.strip():
            raise ValueError("Empty command string")
        
        raw = command_str.strip().lower()
        parts = raw.split()
        
        # Build alias lookup
        alias_map = {}
        for canonical, meta in HOVERBOTCommandParser.command_docs.items():
            for a in meta["aliases"]:
                alias_map[a] = canonical
        
        matched_command = None
        value = None
        
        # Check for ping (no arguments)
        if parts[0] == "ping" or parts[0] == "p":
            if len(parts) != 1:
                raise ValueError("Invalid input: ping takes no arguments")
            matched_command = "Ping"
        elif parts[0] in alias_map:
            if len(parts) != 2:
                raise ValueError("Invalid input: movement requires exactly one numeric argument")
            try:
                value = float(parts[1])
            except ValueError:
                raise ValueError("Invalid input: movement amount must be numerical")
            matched_command = alias_map[parts[0]]
        else:
            raise ValueError("Invalid input: unknown command")
        
        # Translate to ESP32 JSON protocol
        command_token = matched_command.upper().replace(" ", "")  # "Turn Left" -> "TURNLEFT"
        
        if command_token == "PING":
            msg = {
                "id": 1,
                "command": command_token,
                "status": "DISPATCHED",
                "intData": [],
                "floatData": [],
                "result": 0.0,
                "text": ""
            }
        else:
            # Movement commands
            # Forward/Backward: convert meters to milliseconds (1m = 2000ms)
            # Turn: convert degrees to milliseconds (90deg = 500ms)
            if command_token in ["FORWARD", "BACKWARD"]:
                duration_ms = value * 2000.0  # Adjust based on robot speed
            else:  # TURNLEFT, TURNRIGHT
                duration_ms = abs(value) / 90.0 * 500.0  # Adjust based on turn rate
            
            msg = {
                "id": 1,
                "command": command_token,
                "status": "DISPATCHED",
                "intData": [],
                "floatData": [duration_ms],
                "result": 0.0,
                "text": ""
            }
        
        return json.dumps(msg)
    
    @staticmethod
    def list_available_commands():
        print("🧭 Hoverbot Commands:")
        for command, doc in HOVERBOTCommandParser.command_docs.items():
            print(f"- {command}: {doc['description']}. Usage: {doc['usage']}")

def get_parser(robot_type: str) -> RobotCommandParser:
    if robot_type == "R1D4":
        return R1D4CommandParser
    if robot_type == "HOVERBOT":
        return HOVERBOTCommandParser
    else:
        raise ValueError(f"Unknown robot type: {robot_type}")
