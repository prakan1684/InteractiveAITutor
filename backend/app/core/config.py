"""
Configuration file for the backend server.

1. Import os and load_dotenv
2. create settings class using pydantic settings
3. load api keys from environment variables
4. add other settings variables

"""

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    #OpenAI Config
    openai_api_key:str
    openai_model:str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    
    #app config
    app_name: str = "Interactive AI Tutor"
    debug:bool = True


    class Config:
        env_file = ".env"

    
settings = Settings()
