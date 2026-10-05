import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def call_llm(prompt: str) -> str:
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    resp = client.chat.completions.create(
        model="openai/gpt-oss-20b",  # oppure qwen/qwen3.8-27b, 
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content