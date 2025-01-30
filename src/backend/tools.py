import base64
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pdfreader



# Given some message, extracts body of text from the message attachments
def attachment_extraction(service,message,msg_id) -> str:
    text = ""
    if 'parts' not in message['payload']:
        return text
    for part in message['payload']['parts']:
        if part['filename']:
            if 'data' in part['body']:
                data = part['body']['data']
            else:
                att_id = part['body']['attachmentId']
                att = service.users().messages().attachments().get(userId='me', messageId=msg_id,id=att_id).execute()
                data = att['data']
            file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
            path = part['filename']

    return text



# Body is encoded in base64 and is html. In order to pull the raw unstructured text
# we need to decode the html and then extract the text.
def message_body_extraction(service,message,msg_id) -> str:
    if 'data' not in message['payload']['body']:
        return ""
    html = message['payload']['body']['data']
    html = base64.urlsafe_b64decode(html.encode('UTF-8'))
    return html.decode('utf-8')