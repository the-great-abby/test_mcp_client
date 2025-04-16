"""
Model client implementation for handling AI model interactions.
"""
from typing import Dict, Any, AsyncGenerator, Optional, List
import anthropic
import logging
from .config import settings

logger = logging.getLogger(__name__)

class ModelClient:
    """
    Client for interacting with AI models.
    Currently supports Anthropic's Claude models.
    """
    
    def __init__(self):
        """Initialize the model client based on configuration."""
        self.provider = settings.MODEL_PROVIDER
        if self.provider == "anthropic":
            self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unsupported model provider: {self.provider}")
        
        self.model = settings.MODEL_NAME
        self.temperature = settings.MODEL_TEMPERATURE
        self.max_tokens = settings.MODEL_MAX_TOKENS
        logger.info(f"Initialized ModelClient with provider {self.provider}")
    
    async def generate(self, messages: List[Dict[str, Any]], system: Optional[str] = None) -> str:
        """
        Generate a response from the model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system: Optional system message to set context
            
        Returns:
            str: The generated response
        """
        try:
            if self.provider == "anthropic":
                # Convert messages to Anthropic format
                formatted_messages = []
                if system:
                    formatted_messages.append({
                        "role": "system",
                        "content": system
                    })
                
                for msg in messages:
                    role = "assistant" if msg["role"] == "assistant" else "user"
                    formatted_messages.append({
                        "role": role,
                        "content": msg["content"]
                    })
                
                response = await self.client.messages.create(
                    model=self.model,
                    messages=formatted_messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response.content[0].text
            
            raise ValueError(f"Unsupported model provider: {self.provider}")
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            raise
    
    async def stream(self, messages: List[Dict[str, Any]], system: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Stream a response from the model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system: Optional system message to set context
            
        Yields:
            str: Generated text chunks
        """
        try:
            if self.provider == "anthropic":
                # Convert messages to Anthropic format
                formatted_messages = []
                if system:
                    formatted_messages.append({
                        "role": "system",
                        "content": system
                    })
                
                for msg in messages:
                    role = "assistant" if msg["role"] == "assistant" else "user"
                    formatted_messages.append({
                        "role": role,
                        "content": msg["content"]
                    })
                
                stream = await self.client.messages.create(
                    model=self.model,
                    messages=formatted_messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk.content:
                        yield chunk.content[0].text
            
            else:
                raise ValueError(f"Unsupported model provider: {self.provider}")
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}", exc_info=True)
            raise
    
    def format_prompt(self, conversation_messages: List[Dict[str, Any]], system_prompt: Optional[str] = None) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Format conversation messages for the model.
        
        Args:
            conversation_messages: List of conversation messages
            system_prompt: Optional system prompt to set context
            
        Returns:
            tuple: (formatted_messages, system_prompt)
        """
        messages = []
        for msg in conversation_messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages, system_prompt 