from datetime import datetime, timezone

from gemini_interactor import GeminiInteractor
from spreadsheet_interactor import SpreadsheetInteractor

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
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

BLACKLIST_KEYWORDS = [
    "work permit",
    "application number",
    "immigration, refugees and citizenship canada",
    "ircc",
    "immigration, refugee and citizenship canada",
    "embassy",
]

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

CURRENT_WINDOW = '2d'

# If modifying these scopes, delete the file token.json.
SCOPES = [
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/spreadsheets",
]

class JobApplicationTracker:
  def __init__(self, spreadsheet_interactor=None, gemini_interactor=None):

    self.service = None
    self.spreadsheet_interactor = spreadsheet_interactor
    self.gemini_interactor = gemini_interactor

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
      self.service = build("gmail", "v1", credentials=creds)

    except HttpError as error:
      # TODO(developer) - Handle errors from gmail API.
      print(f"An error occurred: {error}")


  def _extract_new_message_ids(self) -> list[str]:
    if self.service is None:
      raise RuntimeError('Gmail service not initialized in extract new messages')

    msg_ids = []
    messages = self.service.users().messages().list(userId="me", q=f"newer_than:{CURRENT_WINDOW}").execute()

    for message in messages['messages']:
      msg_ids.append(message['id'])

    return msg_ids

  def _check_keywords(self, email_data) -> bool:
    subject_line = email_data["subject"].lower()
    content = email_data['content'].lower()

    for category, keywords in keyword_categories.items():
      for keyword in keywords:
        if keyword in subject_line or keyword in content:
          print(f'Found {category} email')
          print(email_data)
          return True
    return False

  def _check_private(self, email_data) -> bool:
    subject_line = email_data["subject"].lower()
    content = email_data['content'].lower()

    for keyword in BLACKLIST_KEYWORDS:
      if keyword in subject_line or keyword in content:
        return True
    return False


  def _extract_body(self, message_id):
    if self.service is None:
      raise RuntimeError('Gmail service not initialized in extract body')
    
    full_message = self.service.users().messages().get(userId="me", id=message_id, format='raw').execute()

    if full_message:
      raw_email = full_message['raw']

      email_bytes = base64.urlsafe_b64decode(raw_email)
      email_message = BytesParser(policy=policy.default).parsebytes(email_bytes)

      subject = email_message['Subject']
      sender = email_message['From']

      body = email_message.get_body(preferencelist=("plain", "html"))

      sent_date = parsedate_to_datetime(email_message["Date"])

      if body:
        content = body.get_content()

        # Remove HTML if necessary
        if body.get_content_type() == "text/html":
          content = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)

        # Normalize whitespace
        content = re.sub(r"\s+", " ", content).strip()

        email_data = {
          "id": message_id,
          "sender": sender,
          "subject": subject,
          "content": content,
          "date": sent_date
        }

        return email_data

  def _process(self, emails):
    for email in emails:
      result = None

      if isinstance(self.gemini_interactor, GeminiInteractor):
        result = self.gemini_interactor.prompt(email['content'])

      if result and isinstance(self.spreadsheet_interactor, SpreadsheetInteractor):
        self.spreadsheet_interactor.add_to_spreadsheet(email, result)

  def run(self):
    emails = []

    to_process = []

    existing_ids = self.spreadsheet_interactor.get_existance_set()

    msg_ids = self._extract_new_message_ids()

    for id in msg_ids:
      if id in existing_ids:
        continue

      email_data = self._extract_body(id)

      if email_data:
        emails.append(email_data)

    for email in emails:
      private = self._check_private(email)

      if private:
        continue

      check = self._check_keywords(email)

      if check:
        to_process.append(email)

    self._process(to_process)

if __name__ == "__main__":
  # main()
  gemini_interactor = GeminiInteractor()
  spreadsheet_interactor = SpreadsheetInteractor()
  job_app_tracker = JobApplicationTracker(gemini_interactor=gemini_interactor, spreadsheet_interactor=spreadsheet_interactor)
  job_app_tracker.run()