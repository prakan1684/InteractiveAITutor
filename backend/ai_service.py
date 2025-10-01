import openai
from config import settings

client = openai.OpenAI(api_key=settings.openai_api_key)

async def chat_with_ai(message: str, context: str = None) -> str:
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a helpful AI tutor. You explain concepts clearly and help students learn effectively."
            }
        ]

        if context:
            messages.append({
                "role": "system",
                "content": f"Use this context to help answer questions: {context}"
            })
                
        # Add user's message
        messages.append({
            "role": "user",
            "content": message
        })

        # Call OpenAI API - FIXED VERSION
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error: {e}")
        return f"I'm sorry, I encountered an error: {str(e)}"