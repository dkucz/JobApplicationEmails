import os.path
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from bs4 import BeautifulSoup

import base64
import re
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup

APPLICATION_KEYWORDS = [
    "application received",
    "application submitted",
    "thank you for applying",
    "thanks for applying",
    "we received your application",
    "your application for",
    "application confirmation",
    "successfully applied",
    "confirmation of your application",
]

INTERVIEW_KEYWORDS = [
    "interview invitation",
    "invite you to interview",
    "schedule an interview",
    "interview availability",
    "online assessment",
    "coding assessment",
    "technical assessment",
    "assessment invitation",
]

UPDATE_KEYWORDS = [
    "application update",
    "update on your application",
    "status of your application",
    "moving forward with your application",
    "not moving forward",
    "unable to proceed",
    "offer of employment",
    "offer letter",
]

keyword_categories = {
  'application': APPLICATION_KEYWORDS,
  'interview': INTERVIEW_KEYWORDS,
  'update': UPDATE_KEYWORDS
}

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)
    # results = service.users().labels().list(userId="me").execute()
    # labels = results.get("labels", [])
    messages = service.users().messages().list(userId="me", maxResults=10).execute()

    if not messages:
      print("no messages")
    else:
      execute = True
      for message in messages['messages']:
        message_id = message['id']

        extract_body(service=service, message_id=message_id)

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


def extract_body(service, message_id) -> None:
  full_message = service.users().messages().get(userId="me", id=message_id, format='raw').execute()

  if full_message:
    raw_email = full_message['raw']

    email_bytes = base64.urlsafe_b64decode(raw_email)
    email_message = BytesParser(policy=policy.default).parsebytes(email_bytes)

    subject = email_message['Subject']
    sender = email_message['From']

    body = email_message.get_body(preferencelist=("plain", "html"))

    if body:
      content = body.get_content()

      # Remove HTML if necessary
      if body.get_content_type() == "text/html":
        content = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)

      # Normalize whitespace
      content = re.sub(r"\s+", " ", content).strip()

      email_data = {
        "sender": sender,
        "subject": subject,
        "content": content
      }

      check_keywords(email_data=email_data)

def check_keywords(email_data) -> None:
  subject_line = email_data['subject']
  content = email_data['content']

  for category, keywords in keyword_categories.items():
    for keyword in keywords:
      if keyword in subject_line or keyword in content:
        print(f'Found {category} email')
        print(email_data)
        return

  print('Not a job email')

if __name__ == "__main__":
  main()