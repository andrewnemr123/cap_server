from abc import ABC, abstractmethod
from encodings.aliases import aliases

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
        command, err = None, None
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
            return f"[{{\"command\":\"move\", \"float_data\":[{value}]}}]"
        if verb in R1D4CommandParser.commands_docs["Turn"]["aliases"]:
            return f"[{{\"command\":\"turn\", \"float_data\":[{value}]}}]"

        raise ValueError("Invalid input: unknown command")
    
    @staticmethod
    def list_available_commands():
        print("🧭 Manual Mode Active! Available Commands:")
        for command, doc in R1D4CommandParser.commands_docs.items():
            print(f"- {command}: {doc['description']}. Usage: {doc['usage']}")
        pass

# {"id":1,"command":"FORWARD","status":"DISPATCHED","intData":[10],"floatData":[12.3],"result":0.0,"text":""}
class HOVERBOTCommandParser(RobotCommandParser):
    command_docs = {
        "Forward":  {"aliases":["forward", "f"],          "description": "Move robot forward by specified meters",  "usage": "forward <meters:float>",      "example": "forward 1.0"},
        "Backward": {"aliases":["backward", "b"],         "description": "Move robot backward by specified meters", "usage": "backward <meters:float>",     "example": "backward 1.0"},
        "Left":     {"aliases":["left", "l"],             "description": "Strafe left by specified meters",         "usage": "left <meters:float>",         "example": "left 0.5"},
        "Right":    {"aliases":["right", "r"],            "description": "Strafe right by specified meters",        "usage": "right <meters:float>",        "example": "right 0.5"},
        "Ping LIDAR":      {"aliases":["ping lidar", "pl"],       "description": "Ping the LIDAR sensor",      "usage": "ping lidar",      "example": "ping lidar"},
        "Ping 3D Camera":  {"aliases":["ping 3d camera", "p3c"],  "description": "Ping the 3D camera sensor",  "usage": "ping 3d camera",  "example": "ping 3d camera"},
    }

    @staticmethod
    def parse_command(command_str: str) -> str:
        if not command_str or not command_str.strip():
            raise ValueError("Empty command string")
        raw = command_str.strip().lower()
        parts = raw.split()

        # Build alias lookup (alias -> canonical command key)
        alias_map = {}
        for canonical, meta in HOVERBOTCommandParser.command_docs.items():
            for a in meta["aliases"]:
                alias_map[a] = canonical

        matched_command = None
        value = None

        # Try multi-word aliases first (sensor pings)
        if len(parts) >= 2:
            two_word = " ".join(parts[:2])
            if two_word in alias_map and alias_map[two_word].startswith("Ping"):
                if len(parts) != 2:
                    raise ValueError("Invalid input: sensor ping takes no numeric argument")
                matched_command = alias_map[two_word]

        # Single-word movement or abbreviated forms
        if not matched_command:
            if parts[0] in alias_map:
                canonical = alias_map[parts[0]]
                if canonical.startswith("Ping"):
                    if len(parts) > 2:
                        raise ValueError("Invalid input: sensor ping takes no numeric argument")
                    matched_command = canonical
                else:
                    if len(parts) != 2:
                        raise ValueError("Invalid input: movement requires exactly one numeric argument")
                    try:
                        value = float(parts[1])
                    except ValueError:
                        raise ValueError("Invalid input: movement amount must be numerical")
                    matched_command = canonical

        if not matched_command:
            raise ValueError("Invalid input: unknown command")

        # Translate to Hoverbot legacy JSON protocol
        command_token = matched_command.upper().replace(" ", "")  # e.g., "Ping LIDAR" -> "PINGLIDAR"

        if command_token.startswith("PING"):
            # Sensor pings carry no payload
            return (
                "{"
                f"\"command\":\"{command_token}\"," 
                "\"intData\":[],\"floatData\":[],\"status\":\"DISPATCHED\",\"result\":0.0,\"text\":\"\""
                "}"
            )
        else:
            # Movement with one float argument (meters)
            return (
                "{"
                f"\"command\":\"{command_token}\"," 
                "\"intData\":[],\"floatData\":[" + str(value) + "],\"status\":\"DISPATCHED\",\"result\":0.0,\"text\":\"\""
                "}"
            )

    @staticmethod
    def list_available_commands():
        print("🧭 Hoverbot Commands:")
        for command, doc in HOVERBOTCommandParser.command_docs.items():
            print(f"- {command}: {doc['description']}. Usage: {doc['usage']}")
    
def get_parser(robotType:str) -> RobotCommandParser:
    if robotType == "R1D4":
        return R1D4CommandParser()
    if robotType == "HOVERBOT":
        return HOVERBOTCommandParser()
    else:
        raise ValueError(f"Unknown robot type: {robotType}")
