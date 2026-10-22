import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()

class JobEmail(BaseModel):
    job_role: str = Field(description="Specific job title applied for, or empty if not a job email")
    company: str = Field(description="Company applied to, or empty if not a job email")
    is_job_email: bool = Field(description="Is this a job email or not")
    email_type: str = Field(description="The type of job-related email: application_confirmation, interview, assessment, rejection, offer, update, or other")
    application_status: str = Field(description="One word that represents status of the job, one of applied, interviewing, rejected, or offer")
    job_location: str = Field(description="Location of the job if in email, otherwise leave blank")
    next_action: str = Field(description="The next action the user should take")

class GeminiInteractor:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = os.getenv('GEMINI_MODEL')
        self.client = genai.Client()

    def prompt(self, email_content):
        input_prompt = f"Evaluate whether this is a job email or not: {email_content}"

        interaction = self.client.interactions.create(
            model=self.model,
            input=input_prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": JobEmail.model_json_schema()
            },
        )

        job_email = JobEmail.model_validate_json(interaction.output_text)
        return job_email