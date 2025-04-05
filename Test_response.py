from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    model="gpt-4o",
    input=[
        {
            "role": "user",
            "content": "Search https://techcrunch.com/tag/ai/ and https://openai.com/blog for today's AI articles. Return titles and links."
        }
    ],
    tools=["web_search"]
)

print("📦 GPT RESPONSE:")
print(response.output_text)
