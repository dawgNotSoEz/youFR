from groq import Groq
from dotenv import load_dotenv
import os

# load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# debug check
print("API KEY FOUND:", GROQ_API_KEY is not None)

client = Groq(api_key=GROQ_API_KEY)

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "user", "content": "Verify: Einstein won Nobel Prize for relativity"}
    ]
)

print(response.choices[0].message.content)