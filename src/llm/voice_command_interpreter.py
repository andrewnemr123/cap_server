import os
from openai import OpenAI
from pydantic import BaseModel, root_model
from typing import Literal

class CommandType(BaseModel):
    command: Literal["move", "turn"]
    float_data: list[float]

class ResponseType(BaseModel):
    root_model: list[CommandType]

openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


new_prompt = """You are an assistant that converts natural
              language instructions into a JSON array of robot commands.
              Each command must be in the format: {\"command\": \"move/turn\", \"float_data\": [value]}.
             
             You use 'move' or 'turn' to describe actions, or return an empty array if irrelevant.
              - 'turn' indicates rotation (e.g., left = -90, right = 90)
              - 'move' indicates movement in meters
            """

def interpretSeriesOfCommands(order: str) -> str:
    response = openai.chat.completions.parse(
        model="gpt-5-nano",
        response_format=ResponseType,
        messages=[
            {"role": "system", "content": new_prompt},
            {"role": "user", "content": f"Execute the order: '{order}'."}
        ],
        max_tokens=100,
        temperature=0
    )
    return response.choices[0].message.strip()
