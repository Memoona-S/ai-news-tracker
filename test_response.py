from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    model="gpt-4o",
    input=[
        {
            "role": "user",
            "content": "Search the following sites and return today's AI-related articles with title and link:\n\n1. https://techcrunch.com/tag/ai/\n2. https://openai.com/blog"
        }
    ],
    tools=[
        {
            "type": "tool",
            "tool": "web_search"
        }
    ]
)

print("📦 GPT RESPONSE:")
print(response.output_text)
