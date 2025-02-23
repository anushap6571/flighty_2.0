import base64
from datetime import datetime
import os
from bs4 import BeautifulSoup, Comment
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pdfreader

from schemas import Attachment


# Given some message, extracts body of text from the message attachments
def attachment_extraction(service,message,msg_id) -> list[str] | None:
    text = None
    attachments = []
    if 'parts' not in message['payload']:
        return text
    for part in message['payload']['parts']:
        if part['filename']:
            if 'data' in part['body']:
                data = part['body']['data']
                attachments.append(Attachment.validate_base64(data))
            else:
                att_id = part['body']['attachmentId']
                att = service.users().messages().attachments().get(userId='me', messageId=msg_id,id=att_id).execute()
                data = att['data']
                attachments.append(Attachment.validate_base64(data))

    return attachments



# Body is encoded in base64 and is html. In order to pull the raw unstructured text
# we need to decode the html and then extract the text.
def extrace_html_from_gmail_payload(service,message,msg_id) -> str:
    if 'data' not in message['payload']['body']:
        return ""
    html = message['payload']['body']['data']
    html = base64.urlsafe_b64decode(html.encode('UTF-8'))
    return html.decode('utf-8')


def extract_unstructured_html(html: str | None, filename: str | None = None) -> str:
    raw_html = ""
    if (filename):
        with open(file=filename, mode='r') as html_file:
            raw_html = html_file.read()
    elif(html):
        raw_html = html

    soup = BeautifulSoup(raw_html, 'html.parser')
    
    unwanted_tags = [
        'script', 'style', 'noscript', 'head', 'meta',
        'link', 'title', 'svg', 'footer', 'header', 'nav', 'aside'
    ]
    
    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()
    
    for link in soup.find_all('a'):
        href = link.get('href')
        if href:
            link_text = link.get_text().strip()
            link.replace_with(f"{link_text}")  # Replace link with text + URL
    
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()
    
    visible_text = soup.get_text(separator='\n')
    lines = (line.strip() for line in visible_text.splitlines())
    chunks = [chunk for chunk in lines if chunk]
    cleaned_text = '\n'.join(chunks)
    
    return cleaned_text


if __name__ == "__main__":
    for root, dirs, files in os.walk('./data'):
        for filename in files:
            extracted = extract_unstructured_html(html=None, filename=os.path.join(root, filename))