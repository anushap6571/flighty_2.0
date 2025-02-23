import base64
import email
from typing import Any
from pydantic import BaseModel, Field

import abc
import json


JSON_PROMPT : str = f"Your response should be in JSON format ONLY. \
Do NOT include any other output in your response. \
Below is the JSON format your output should be in with additional information for each field:"


class Attachment():
    def __init__(self):
        pass
    
    def to_base64(self) -> str:
        return ""
    
    # Returns base64 string after validating it
    # if the base64 is binary we decode it then convert it to string
    # input MUST be some version of base64 encoded data
    @classmethod
    def validate_base64(cls, to_validate) -> str:
        if type(to_validate) is str:
            return to_validate
        elif type(to_validate) is bytes:
            return base64.b64decode(s=to_validate, validate=True).decode()
        else:
            raise Exception()

class AIEmailPayload:
    def __init__(self, text_context: dict[str,str], 
                 attachments: list[Attachment]| None,
                 id: str):
        """
        @param text_context -> a mapping of context keys in the prompt to their values
        """
        self.text_context = text_context
        self.attachments = attachments
        self.id = id

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
    airport_code_src: str | None = Field(
        description="Airport code in ICAO or IATA format"
    )

    airport_code_dst: str | None = Field(
        description="Airport code in ICAO or IATA format"
    )
    flight_takeoff_date: str | None = Field(
        description="Date the flight is taking off in yyyy-mm-dd format (ISO_LOCAL_DATE in python datetime)"
    )
    flight_number: str | None = Field(
        description="An IATA or ICAO airline code followed by the flight number"
    )
    passenger_name: str | None

    @classmethod
    def get_user_prompt(cls, content: dict[str, Any]) -> str:
        return """\
Any attachments on the email are attached to this prompt.
Passenger Name: {name}
Extracted Text from HTML Body of email: 
                \"{html_text}\"""".format(**content)

    @classmethod
    def get_system_prompt(cls, json_schema: dict) -> str:
        sys_prompt = f"""You are an email analyzer that ONLY responds in JSON format. Your parse unstructured data extracted from HTML in emails. You also parse \
unstructured from PDF attachments on emails. These two modes of data will be part of your inputs. Your job is to, first, determine whether the input contains a flight \
booking or boarding pass for the specified user (you will be given this users name). If you are confident that the input contains a flight booking for the specified user,\
your next task is to extract information from the inputs. The information you are extracting is specified in the JSON schema below. You should ensure that you ONLY extract data from the inputs if you believe the inputs are tied \
to a flight booking/ticket or boarding pass AND they are tied to the specific user. In any other case you should return an empty JSON like this: {json.dumps({})}. DO NOT include any additional text besides the JSON.
        """
        #TODO maybe change this to a format string and move up into AB class
        # TODO move system base prompts to a file? Better formatting?
        return '\n'.join([sys_prompt, JSON_PROMPT, json.dumps(json_schema)])


class SanityCheck(Promptable):
    is_there_text_in_the_prompt: bool = Field(
        description="True if there is the text you are searching for in the prompt, False otherwise"
    )

    @classmethod
    def get_system_prompt(cls, json_schema: dict) -> str:
        sys_prompt = f"""You are a tool that checks if there is a specific word or phrase in a piece of text. \
The specific piece of text you will be searching through will be provided in the prompt"""
        #TODO maybe change this to a format string and move up into AB class
        return '\n'.join([sys_prompt, JSON_PROMPT, json.dumps(json_schema)])
    

    @classmethod
    def get_user_prompt(cls, content: dict[str, Any]) -> str:
        return """Does the following text contain the word {word}? The text is \"{text}\" """.format(**content)