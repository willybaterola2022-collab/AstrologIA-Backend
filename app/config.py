from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_jwt_secret: str

    class Config:
        env_file = ".env"

settings = Settings()
