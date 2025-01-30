from typing import Any
from pydantic import BaseModel

import abc
import json


JSON_PROMPT : str = f"Your response should be in JSON format ONLY. \
Do NOT include any other output in your response. \
Below is the JSON format your output should be in:"

class Promptable(BaseModel, abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_system_prompt(cls, json_schema: dict) -> str:
        pass

    
    @classmethod
    @abc.abstractmethod
    def get_user_prompt(cls, content: dict[str, Any]) -> str:
        pass
        


class ExtractedFlightInfo(Promptable):
    airport_code_src: str | None
    airport_code_dst: str | None
    flight_takeoff_time: str | None
    flight_landing_time: str | None
    passenger_name: str | None

class SanityCheck(Promptable):
    is_there_text_in_the_prompt: bool

    @classmethod
    def get_system_prompt(cls, json_schema: dict) -> str:
        sys_prompt = f"""Your are a tool that checks if there is a specific word or phrase in a piece of text. \
The specific piece of text you will be searching through will be provided in the prompt"""
        #TODO maybe change this to a format string and move up into AB class
        return '\n'.join([sys_prompt, JSON_PROMPT, json.dumps(json_schema)])
    

    @classmethod
    def get_user_prompt(cls, content: dict[str, Any]) -> str:
        return """Does the following text contain the word {word}? The text is \
        \"{text}\" """.format(**content)