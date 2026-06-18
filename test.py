from groq import Groq
import os

client = Groq(api_key=os.environ["GROQ_API_KEY"])

for m in client.models.list().data:
    print(m.id)


# self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
#         # self.model = "llama-3.1-8b-instant"
#         # self.model = "groq/compound"
#         self.model = "openai/gpt-oss-safeguard-20b"
