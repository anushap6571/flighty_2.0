import json
import time
from typing import Any, Generic, Type, TypeVar, Optional
import typing
import anthropic
import dotenv
from pydantic import BaseModel
from anthropic import Anthropic
import abc

from schemas import ExtractedFlightInfo, Promptable, SanityCheck
import dotenv


dotenv.load_dotenv()


# Generic type variable for the schema
ExtractorSchemaT = TypeVar('ExtractorSchemaT', bound=Promptable)

class Attachment():
    
    def to_base64(self) -> str:
        return ""

class Extractor(Generic[ExtractorSchemaT], abc.ABC):
    """
    Base class for email extractors that parse emails into structured data using LLMs.
    Generic type T must be a Pydantic BaseModel.
    """

    def __init__(self, schema_class: Type[ExtractorSchemaT]):
        self.model_name: str = "base"
        self.SCHEMA_PROMPT = schema_class
    
    @abc.abstractmethod
    async def extract(self, email_content: str) -> ExtractorSchemaT:
        """
        Extract structured information from email content into a Pydantic model.
        
        Args:
            email_content: Raw email content as string
            
        Returns:
            Parsed data in specified Pydantic schema
        """
        pass

    def get_meta_schema(self) -> dict:
        properties = self.SCHEMA_PROMPT.model_json_schema()['properties']
        toReturn = {}
        for k,v in properties.items():
            toReturn[k] = {'type' : v['type']}

        return toReturn 

class ClaudeExtractor(Extractor[ExtractorSchemaT]):
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
                    "params": {
                        "model": "claude-3-5-sonnet-latest",
                        "max_tokens": 1024,
                        "system" : self.SCHEMA_PROMPT.get_system_prompt(self.get_meta_schema()),
                        "messages": [{"role": "user", "content": ai_payload}],
                    },
                }
            )
        messages = self.client.beta.messages.batches.create(
            requests=requests
        )

        while True:
            time.sleep(5)
            status = self.client.beta.messages.batches.retrieve(messages.id)
            if status.processing_status == "ended":
                break

        result_stream = self.client.beta.messages.batches.results(messages.id)

        payload_output: list[ExtractorSchemaT] = []

        for response in result_stream:
            response_content = response.result.model_dump()
            parsed_obj = self.SCHEMA_PROMPT.model_validate_json(response_content['message']['content'][0])
            payload_output.append(parsed_obj)
        return payload_output

if __name__ == "__main__":
    extractor = ClaudeExtractor(schema_class=SanityCheck)
    print(extractor.get_meta_schema())


    payloads = [{'word': "solo", 'text': "solo bolo in the top lane!!!"}]
    attachments = [[]]
    op = extractor.extract(text_payloads=payloads, attachment_payloads=attachments)

