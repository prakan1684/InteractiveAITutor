from pyexpat import model
import openai
from app.core.config import settings
from app.core.logger import get_logger
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel
logger = get_logger(__name__)
client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

class CompletionRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None

class CompletionResponse(BaseModel):
    content: str
    model: str
    tokens_used: int
    finish_reason:str



class AIService:
    def __init__(
        self,
        default_model: str = None,
        default_temperature: float = None,
        default_max_tokens: int = None,
    ):
        self.client = client
        self.model = default_model
        self.temperature = default_temperature
        self.max_tokens = default_max_tokens
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> CompletionResponse:
        """
        Generic completion method for any llm call

        Args:
            messages: list of message dicts with "role" and "content"
            model: model to use
            temperature: temperature to use
            max_tokens: max tokens to use
            response_format: response format to use e.g. {"type": "json_object"}
        """

        try:
            # Use provided model or default, fallback to gpt-4o-mini if neither
            model_to_use = model or self.model or "gpt-4o-mini"
            
            kwargs = {
                "model": model_to_use,
                "messages": messages,
                "temperature": temperature if temperature is not None else (self.temperature if self.temperature is not None else 0.7),
            }
            
            # Only add max_tokens if specified
            if max_tokens or self.max_tokens:
                kwargs["max_tokens"] = max_tokens or self.max_tokens

            if response_format:
                kwargs["response_format"] = response_format

            logger.debug(f"LLM call: model={kwargs['model']}, temp={kwargs['temperature']}")

            response = await self.client.chat.completions.create(**kwargs)
            result = CompletionResponse(
                content=response.choices[0].message.content,
                model=kwargs['model'],
                tokens_used=response.usage.total_tokens,
                finish_reason=response.choices[0].finish_reason
            )
            logger.debug(f"LLM response: {result.tokens_used} tokens, {result.finish_reason}")
            return result
        except Exception as e:
            logger.error(f"Error in complete: {e}")
            raise
    async def complete_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Streaming completion — yields content chunks as they arrive."""
        try:
            model_to_use = model or self.model or "gpt-4o-mini"
            kwargs = {
                "model": model_to_use,
                "messages": messages,
                "temperature": temperature if temperature is not None else (self.temperature if self.temperature is not None else 0.7),
                "stream": True,
            }
            if max_tokens or self.max_tokens:
                kwargs["max_tokens"] = max_tokens or self.max_tokens

            logger.debug(f"LLM stream: model={kwargs['model']}, temp={kwargs['temperature']}")
            stream = await self.client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error in complete_stream: {e}")
            raise

    async def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Method for simple chat interaction with LLM
        Args:
            user_message: user message
            system_prompt: system prompt
            context: context
            conversation_history: conversation history
            **kwargs: additional kwargs
        
        Returns:
            str: response from LLM
        """
            
        messages= []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        else:
            messages.append({
                "role":"system",
                "content": "You are a helpful AI tutor."
            })
        

        #inject context
        if context:
            messages.append({
                "role": "system",
                "content": "Here is the context: \n\n" + context
            })
        
        #inject conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        #user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        response = await self.complete(messages=messages, **kwargs)
        return response.content
    async def classify(
        self,
        text: str,
        classification_prompt: str,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Convenience method for classification tasks with JSON output
        
        Args:
            text: Text to classify
            classification_prompt: Prompt describing classification task
            model: Model to use (defaults to mini for speed/cost)
        
        Returns:
            Parsed JSON dict
        """
        messages = [
            {"role": "user", "content": f"{classification_prompt}\n\nText: {text}"}
        ]
        
        response = await self.complete(
            messages=messages,
            model=model,
            temperature=0.3,  # Lower temp for classification
            response_format={"type": "json_object"}
        )
        
        import json
        return json.loads(response.content)
    
    async def reason(
        self,
        problem: str,
        context: Optional[str] = None,
        model: str = "gpt-4o"
    ) -> str:
        """
        Convenience method for reasoning tasks (chain-of-thought)
        
        Args:
            problem: Problem to reason about
            context: Optional context
            model: Model to use (defaults to gpt-4o for reasoning)
        
        Returns:
            Reasoning steps as string
        """
        system_prompt = """You are an expert reasoning assistant. 
Think step-by-step and show your reasoning process clearly."""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        
        messages.append({"role": "user", "content": problem})
        
        response = await self.complete(
            messages=messages,
            model=model,
            temperature=0.3
        )
        
        return response.content
# Global instance for backward compatibility
_default_service = AIService()
async def chat_with_ai(message: str, context: str = None) -> str:
    """
    Legacy function for backward compatibility
    Use AIService directly for new code
    """
    return await _default_service.chat(
        user_message=message,
        context=context
    )
        
