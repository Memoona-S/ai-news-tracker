from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    model="gpt-4o",
    input=[
        {
            "role": "user",
            "content": "Search https://techcrunch.com/tag/ai/ and https://openai.com/blog for AI articles published today. Return the article title and full link in a bullet list."
        }
    ],
    tool_choice="auto",
    tools=[
        {
            "type": "web_search"
        }
    ]
)

print("📦 GPT RESPONSE:\n")
print(response.output.text)
