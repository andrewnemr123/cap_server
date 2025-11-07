from abc import ABC, abstractmethod

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
        if not command_str:
            err = "Empty command string"
        parts = command_str.split()
        if len(parts) != 2:
            err = "Invalid input: requires 2 arguments"
        for cmd, doc in R1D4CommandParser().commands_docs.items():
            if parts[0].lower() in doc["aliases"]:
                try:
                    amount = float(parts[1])
                    command = f"[{{command:'{cmd.lower()}', float_data:[{amount}]}}]"   
                    break
                except ValueError:
                    err = "Invalid input: movement amount must be numerical"
                
        else:
            err = "Invalid input: unknown command"
        if err:
            raise ValueError(err)
        return command

    @staticmethod
    def list_available_commands():
        print("🧭 Manual Mode Active! Available Commands:")
        for command, doc in R1D4CommandParser.commands_docs.items():
            print(f"- {command}: {doc['description']}. Usage: {doc['usage']}")
        pass

def get_parser(robotType:str) -> RobotCommandParser:
    if robotType == "R1D4":
        return R1D4CommandParser()
    else:
        raise ValueError(f"Unknown robot type: {robotType}")
