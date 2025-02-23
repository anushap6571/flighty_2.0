import json
import time
from typing import Any, Generic, Type, TypeVar, Optional
import typing
import anthropic
import dotenv
from pydantic import BaseModel
from anthropic import Anthropic
import abc
import logging

from schemas import AIEmailPayload, Attachment, ExtractedFlightInfo, Promptable, SanityCheck
import dotenv

dotenv.load_dotenv()


# Generic type variable for the schema
ExtractorSchemaT = TypeVar('ExtractorSchemaT', bound=Promptable)

class Extractor(Generic[ExtractorSchemaT], abc.ABC):
    """
    Base class for email extractors that parse emails into structured data using LLMs.
    Generic type T must be a Pydantic BaseModel.
    """

    def __init__(self, schema_class: Type[ExtractorSchemaT]):
        self.model_name: str = "base"
        self.SCHEMA_PROMPT = schema_class
    
    @abc.abstractmethod
    def extract(self,
                payloads: list[AIEmailPayload]) -> ExtractorSchemaT:
        """
        Extract structured information from email content into a Pydantic model.
        
        Args:
            payloads: Raw email content as string + attachments
            
        Returns:
            Parsed data in specified Pydantic schema
        """
        pass

    def get_meta_schema(self) -> dict:
        properties = self.SCHEMA_PROMPT.model_json_schema()['properties']
        toReturn = {}
        for k,v in properties.items():
            toReturn[k] = {'types' : [v['type']] if 'type' in v else [p['type'] for p in v['anyOf']]}
            if ("description" in v):
                toReturn[k]['description'] = v['description']
        print(toReturn)
        return toReturn 

class ClaudeExtractor(Extractor[ExtractorSchemaT]):
    def __init__(self, 
                 schema_class: Type[ExtractorSchemaT],
                 api_key: str | None = None, 
                 model: str = "claude-3-haiku-20240307"):
        super().__init__(schema_class=schema_class)
        self.model_name = model
        self.client = Anthropic(api_key=api_key)
        
    def extract(self,
                payloads: list[AIEmailPayload]
                ) -> list[ExtractorSchemaT | None]:
        requests = []
        idx = 0

        print(f"Received {len(payloads)} requests")

        for payload in payloads:  
            ai_payload = []

            if payload.attachments:
                for attachment in payload.attachments:
                    pdf_block = {
                        "type" : "document",
                        "source": {
                            "type" : "base64",
                            "media_type": "application/pdf",
                            "data": attachment.to_base64()
                        }
                    }
                    ai_payload.append(pdf_block)
                
            ai_payload.append({'type':'text', 'text': self.SCHEMA_PROMPT.get_user_prompt(content=payload.text_context)})   
            requests.append(
                {
                    "custom_id": payload.id,
                    "params": {
                        "model": self.model_name,
                        "max_tokens": 512,
                        "temperature": 0,
                        "top_p" : 1,
                        "system" : self.SCHEMA_PROMPT.get_system_prompt(self.get_meta_schema()),
                        "messages": [{"role": "user", "content": ai_payload},
                                     # Claude prefill output, starts next token prediction from {
                                     {"role": "assistant", "content": "{"}],
                    },
                }
            )
            idx += 1
        
        print(f"Sending {len(requests)} requests")

        messages = self.client.beta.messages.batches.create(
            requests=requests
        )

        while True:
            time.sleep(10)
            print("Pinging batch service")
            status = self.client.beta.messages.batches.retrieve(messages.id)
            print(f"Status: {status}")
            if status.processing_status == "ended":
                break

        result_stream = self.client.beta.messages.batches.results(messages.id)

        payload_output: list[ExtractorSchemaT | None] = []

        for response in result_stream:
            response_content = response.result.model_dump()
            prefill = '{'
            unvalidated = prefill + response_content['message']['content'][0]['text']
            print(f"Unvalidated Batch Response: {unvalidated}")
            unvalidated = json.loads(unvalidated)
            if unvalidated == {}:
                payload_output.append(None)
            else:
                parsed_obj = self.SCHEMA_PROMPT.model_validate(unvalidated)
                payload_output.append(parsed_obj)
        return payload_output
    


class DeepSeekExtractor(Extractor[ExtractorSchemaT]):
    def __init__(self, 
                 schema_class: Type[ExtractorSchemaT],
                 api_key: str | None = None, 
                 model: str = "claude-3-5-sonnet-latest"):
        super().__init__(schema_class=schema_class)
        self.model_name = model
        self.client = Anthropic(api_key=api_key)
        
    def extract(self,
                text_payloads: list[dict[str, str]], 
                attachment_payloads: list[list[Attachment]]
                ) -> list[ExtractorSchemaT]:
        requests = []
        idx = 0

        for content, attachments_in_payload in zip(text_payloads, attachment_payloads):  
            ai_payload = []

            if attachments_in_payload:
                for attachment in attachments_in_payload:
                    pdf_block = {
                        "type" : "document",
                        "source": {
                            "type" : "base64",
                            "media_type": "application/pdf",
                            "data": attachment.to_base64()
                        }
                    }
                    ai_payload.append(pdf_block)
                
            ai_payload.append({'type':'text', 'text': self.SCHEMA_PROMPT.get_user_prompt(content=content)})   
            requests.append(
                {
                    "custom_id": f"{idx}",
                    "params": {
                        "model": "claude-3-5-sonnet-latest",
                        "max_tokens": 1024,
                        "system" : self.SCHEMA_PROMPT.get_system_prompt(self.get_meta_schema()),
                        "messages": [{"role": "user", "content": ai_payload}],
                    },
                }
            )
            idx += 1
        
        print(f"Requests {requests}")
        messages = self.client.beta.messages.batches.create(
            requests=requests
        )

        while True:
            time.sleep(5)
            logging.info("Pinging batch service")
            status = self.client.beta.messages.batches.retrieve(messages.id)
            if status.processing_status == "ended":
                break

        result_stream = self.client.beta.messages.batches.results(messages.id)

        payload_output: list[ExtractorSchemaT] = []

        for response in result_stream:
            response_content = response.result.model_dump()
            unvalidated = json.loads(response_content['message']['content'][0]['text'])
            logging.debug(f"Unvalidated Batch Response: {unvalidated}")
            parsed_obj = self.SCHEMA_PROMPT.model_validate_json(unvalidated)
            payload_output.append(parsed_obj)
        return payload_output

if __name__ == "__main__":
    extractor = ClaudeExtractor(schema_class=ExtractedFlightInfo)
    payloads = [{'name': "Shrey Patel", 'html_text': "Train Ticket, Depart January 5th 2024 Arrive January 6th 2027"}]
    attachments = [[]]
    op = extractor.extract(text_payloads=payloads, attachment_payloads=attachments)

