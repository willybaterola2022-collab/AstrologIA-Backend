from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_jwt_secret: str = "default_placeholder_secret_replace_me_in_railway"

    class Config:
        env_file = ".env"

settings = Settings()
