import asyncio
import ollama
from typing import Optional
import json

async def generate_code_exercise(topic: str) -> str:
    """Generates an educational code exercise using Ollama with gpt-oss:20b model."""
    prompt = """
    Generate a Python code exercise with the following characteristics:
    - A realistic function solving a common task
    - Contains 1-2 subtle but educational bugs
    - Includes comments explaining expected behavior
    - Maximum 15 lines of code
    - Focus on common Python patterns and best practices
    
    Return only the code without explanations.
    """

    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            response = await ollama.generate(
                model="gpt-oss:20b",
                prompt=prompt,
                options={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "max_length": 300
                }
            )
            return response['response'].strip()
        except Exception as e:
            if attempt == max_retries - 1:
                return f"Error generating exercise: {e}"
            await asyncio.sleep(retry_delay)

async def get_feedback(user_review: str, solution: str) -> str:
    """Provides educational feedback using gpt-oss:20b model."""
    prompt = f"""
    Review this code review feedback:
    Code: {solution}
    Review: {user_review}
    
    Provide a 3-part response:
    1. Highlight correct observations
    2. Note any missed issues
    3. One specific improvement tip
    
    Keep it concise and constructive.
    """

    try:
        response = await ollama.generate(
            model="gpt-oss:20b",
            prompt=prompt,
            options={
                "temperature": 0.7,
                "top_p": 0.95,
                "max_length": 200
            }
        )
        return response['response'].strip()
    except Exception as e:
        return f"Error generating feedback: {e}"