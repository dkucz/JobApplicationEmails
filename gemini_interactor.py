import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()

class JobEmail(BaseModel):
    job_role: str = Field(description="Specific job title applied for, or empty if not a job email")
    company: str = Field(description="Company applied to, or empty if not a job email")

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
        print(job_email)