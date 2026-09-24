from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    spotify_client_id: str
    spotify_client_secret: SecretStr
    spotify_redirect_uri: str
    jwt_secret_key: str

settings = Settings()