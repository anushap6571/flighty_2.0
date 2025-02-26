import os.path
from datetime import datetime
from time import sleep
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from dotenv import load_dotenv
from tools import attachment_extraction, message_body_extraction
from firstpass import generate_firstpass_query
from anthropic import Anthropic
# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDS = "../../credentials.json"
load_dotenv()

def main():
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          CREDS, SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    # Call the Gmail API
    search_query = generate_firstpass_query()
    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId='me', labelIds=['INBOX'],maxResults=5000, q=search_query).execute()
    messages = results.get('messages', [])

    while 'nextPageToken' in results:
        page_token = results['nextPageToken']
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], pageToken=page_token, maxResults=5000,q=search_query).execute()
        messages.extend(results.get('messages', []))
    

    print(f"Total messages found: {len(messages)}")


    for msg in messages:
        message = service.users().messages().get(userId='me', id=msg['id']).execute()
        subject = ''
        msg_id = ''
        for header in message['payload']['headers']:
            if header['name'] == 'Subject':
                subject = header['value']
            if header['name'] == 'Message-ID':
               msg_id = header['value']        
        print(f"Message ID: {msg_id}")
        print(f"Subject: {subject}\nDate: {datetime.fromtimestamp(float(message['internalDate'])/1000).strftime('%Y-%m-%d %H:%M:%S')}")

        # filename = f"data/email_{msg['id']}_{message['internalDate']}.html"
        # file = attachment_extraction(service,message,msg['id'])

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()
