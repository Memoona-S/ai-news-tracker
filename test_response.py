from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    model="gpt-4o",
    input=[
        {
            "role": "user",
            "content": "Search https://techcrunch.com/tag/ai/ and https://openai.com/blog for AI articles published today. Return the article title and full link in a two column list to paste in word."
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

found_text = False
for block in response.output:
    print(f"🔍 Block type: {block.type}")  # 👈 show what's coming back
    if block.type == "text":
        found_text = True
        print(block.text)

if not found_text:
    print("⚠️ No text output from GPT. It may have used a tool but not returned readable content.")
