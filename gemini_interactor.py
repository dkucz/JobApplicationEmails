import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

class GeminiInteractor:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = os.getenv('GEMINI_MODEL')
        self.client = genai.Client()

    def prompt(self, email_content):
        input_prompt = f"Evaluate whether this is a job email or not: {email_content}"

        interaction = self.client.interactions.create(
            model=self.model,
            input=input_prompt
        )

        print(interaction.output_text)