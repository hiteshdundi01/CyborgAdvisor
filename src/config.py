"""
Cyborg Advisor Configuration Module

Provides configurable model selection for any Google Gemini model.
Supports dynamic model instantiation for future model releases.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()


class ModelConfig:
    """Configuration for Google Gemini models with full flexibility."""
    
    # Default model - can be overridden via environment or at runtime
    DEFAULT_MODEL = "gemini-2.0-flash"
    
    # Supported model families (non-exhaustive, any Google model works)
    KNOWN_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
    ):
        """
        Initialize model configuration.
        
        Args:
            model_name: Google model name (defaults to env or gemini-2.0-flash)
            temperature: Model temperature for response randomness
            max_tokens: Maximum tokens in response
            api_key: Google API key (defaults to environment variable)
        """
        self.model_name = model_name or os.getenv("MODEL_NAME", self.DEFAULT_MODEL)
        self.temperature = float(os.getenv("MODEL_TEMPERATURE", temperature))
        self.max_tokens = int(os.getenv("MODEL_MAX_TOKENS", max_tokens))
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found. Set it in .env file or pass directly."
            )
    
    def get_llm(self) -> ChatGoogleGenerativeAI:
        """
        Create and return a LangChain chat model instance.
        
        Returns:
            ChatGoogleGenerativeAI: Configured LLM instance
        """
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            google_api_key=self.api_key,
        )
    
    def switch_model(self, new_model: str) -> "ModelConfig":
        """
        Create a new config with a different model.
        
        Args:
            new_model: Name of the new Google model to use
            
        Returns:
            ModelConfig: New configuration instance
        """
        return ModelConfig(
            model_name=new_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=self.api_key,
        )


# Global default configuration instance
default_config = None


def get_config(model_name: Optional[str] = None) -> ModelConfig:
    """
    Get or create the default model configuration.
    
    Args:
        model_name: Optional model name override
        
    Returns:
        ModelConfig: Configuration instance
    """
    global default_config
    
    if model_name:
        return ModelConfig(model_name=model_name)
    
    if default_config is None:
        default_config = ModelConfig()
    
    return default_config


def get_llm(model_name: Optional[str] = None) -> ChatGoogleGenerativeAI:
    """
    Convenience function to get a configured LLM instance.
    
    Args:
        model_name: Optional model name override
        
    Returns:
        ChatGoogleGenerativeAI: Ready-to-use LLM instance
    """
    return get_config(model_name).get_llm()
