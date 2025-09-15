import ollama

async def generate_code_exercise(topic: str) -> str:
    """Generates a code exercise with a bug using Ollama."""
    prompt = (
        f"Generate a simple Python code function about {topic}. "
        "The code should contain a subtle but common bug. "
        "The response should only be the code block, without any explanation. "
        "For example, a list index out of bounds error, an off-by-one error, "
        "or a type mismatch."
    )
    try:
        response = ollama.generate(model="gpt-oss:20b", prompt=prompt)
        return response['response'].strip()
    except Exception as e:
        return f"Error generating exercise: {e}"

async def get_feedback(user_code: str, solution: str) -> str:
    """Provides AI feedback on the user's code against the solution."""
    prompt = (
        f"Here is a code snippet with a bug:\n\n{solution}\n\n"
        f"The user attempted to fix it with this code:\n\n{user_code}\n\n"
        "Explain what was wrong with the original code, and how the user's "
        "fix addresses (or fails to address) the bug. "
        "Keep the explanation concise and to the point."
    )
    try:
        response = ollama.generate(model="llama3.1", prompt=prompt)
        return response['response'].strip()
    except Exception as e:
        return f"Error getting feedback: {e}"