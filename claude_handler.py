import httpx
import os

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

async def get_claude_response(user_query: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 300,
                "system": (
                    "You are a helpful assistant for Collegedunia, India's largest college review platform. "
                    "Answer questions about colleges, exams, courses, admissions, and study abroad concisely. "
                    "Keep responses under 200 words. Use plain text, no markdown formatting."
                ),
                "messages": [{"role": "user", "content": user_query}]
            },
            timeout=10.0
        )
        data = response.json()
        return data["content"][0]["text"]
