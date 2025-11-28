import os
from typing import Literal
from pydantic import BaseModel, root_model

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # library missing
    OpenAI = None  # fallback sentinel


class CommandType(BaseModel):
    command: Literal["move", "turn"]
    float_data: list[float]

class ResponseType(BaseModel):
    root_model: list[CommandType]

_OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
_openai_client = None
if OpenAI and _OPENAI_API_KEY:
    try:
        _openai_client = OpenAI(api_key=_OPENAI_API_KEY)
    except Exception:
        _openai_client = None

_PROMPT = (
    "You are an assistant that converts natural language instructions into a JSON array of robot commands. "
    "Each command must be in the format: {\"command\": \"move/turn\", \"float_data\": [value]}. "
    "Use 'move' or 'turn' only, or return an empty array if irrelevant. "
    "'turn' indicates rotation (left = -90, right = 90). 'move' indicates meters moved."
)

def interpretSeriesOfCommands(order: str) -> str:
    """Return JSON array of parsed commands, or [] if model unavailable.

    Falls back to naive rule-based interpretation if OpenAI is not configured.
    """
    if not _openai_client:
        # Fallback: very simple heuristic
        order_lc = order.lower()
        out = []
        # Extract simple patterns like 'move 2', 'turn 90'
        import re
        for match in re.finditer(r"\b(move|turn)\s+(-?\d+(?:\.\d+)?)", order_lc):
            cmd = match.group(1)
            val = float(match.group(2))
            out.append({"command": cmd, "float_data": [val]})
        return str(out).replace("'", '"')  # JSON-like string

    response = _openai_client.chat.completions.parse(
        model="gpt-5-nano",
        response_format=ResponseType,
        messages=[
            {"role": "system", "content": _PROMPT},
            {"role": "user", "content": f"Execute the order: '{order}'."}
        ],
        max_tokens=100,
        temperature=0
    )
    return response.choices[0].message.strip()
