import os
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from dotenv import set_key

SCOPES = [
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/spreadsheets",
]

load_dotenv()

class SpreadsheetInteractor:
    def __init__(self):
        self.service = None
        creds = None
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
            self.service = build("sheets", "v4", credentials=creds)
            self.spreadsheet_id = os.getenv('SPREADSHEET_ID')
            self.range = "Sheet1!A1:H1"

            if not self.spreadsheet_id:
                print("No spreadsheet ID configured. Please create a spreadsheet first.")
                raise RuntimeError

        except HttpError as error:
            print(error)

    def get_existance_set(self) -> set:
        range = "Sheet1!H2:H"

        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range
        ).execute()

        values = result.get("values", [])

        return {col[0] for col in values if col and col[0]}

    def get_existance_set(self) -> set:
        range = "Sheet1!H2:H"
        result = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=range).execute()
        values = result.get("values", [])

        message_ids = set()

        for col in values:
           if col[0] not in message_ids and col[0]:
              message_ids.add(col[0])

        return message_ids

    def add_to_spreadsheet(self, email_data, gemini_result):
        date = email_data.get("date")
        date = date.isoformat() if date else "Unknown"

        self.service.spreadsheets().values().append(
           spreadsheetId=self.spreadsheet_id,
           range="Sheet1!A:H",
           valueInputOption="RAW",
           insertDataOption="INSERT_ROWS",
           body={
              "values": [[
                date,
                gemini_result.company or "Unknown",
                gemini_result.job_role or "Unknown",
                gemini_result.email_type or "Unknown",
                gemini_result.application_status or "Unknown",
                gemini_result.job_location or 'Unknown',
                gemini_result.next_action or "Unknown",
                email_data['id']
              ]]
           } 
        ).execute()
        return True

    def create_spreadsheet(self):
        creds = None
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
            service = build("sheets", "v4", credentials=creds)
            spreadsheet = service.spreadsheets().create(
                body={
                    "properties": {
                        "title": "Job Application Tracker"
                    }
                }
            ).execute()

            spreadsheet_id = spreadsheet["spreadsheetId"]

            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=self.range,
                valueInputOption="RAW",
                body={
                    "values": [[
                        "Date Received",
                        "Company",
                        "Job Title",
                        "Email Type",
                        "Application Status",
                        "Job Location",
                        "Next Action",
                        "Gmail Message ID"
                    ]]
                }
            ).execute()

            print("Please copy and update Github Action Secrets with the Spreadsheet ID")
            print(f"A spreadsheet was created with the following ID: {spreadsheet_id}")

        except HttpError as error:
            print(f'An error occured while trying to create the spreadsheet: {error}')

if __name__ == '__main__':
    spreadsheet_interactor = SpreadsheetInteractor()
    spreadsheet_interactor.create_spreadsheet()