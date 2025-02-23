import os
from tools import extract_unstructured_html
from model import ClaudeExtractor
from schemas import AIEmailPayload, ExtractedFlightInfo
import json
import pathlib


if __name__ == "__main__":
    payloads = []
    for root, dirs, files in os.walk('./data'):
        for filename in files:
            extracted = extract_unstructured_html(html=None, filename=os.path.join(root, filename))
            if len(extracted) == 0:
                continue
            payloads.append({"payload": {'name': "Shrey Patel", 'html_text': extracted}, "id": filename})

    extractor = ClaudeExtractor(schema_class=ExtractedFlightInfo)
    payloads = [AIEmailPayload(text_context=payload['payload'],attachments=None, id=payload['id']) for payload in payloads]
    op = extractor.extract(payloads)
    
    # Create outputs directory if it doesn't exist
    output_dir = pathlib.Path('./outputs')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save each schema as a JSON file
    for i, schema in enumerate(op):
        output_file = output_dir / f'{filenames[i]}.json'
        with open(output_file, 'w') as f:
            if schema is not None:
                json.dump(schema.model_dump(), f, indent=2)
            else:
                json.dump({}, f, indent=2)
