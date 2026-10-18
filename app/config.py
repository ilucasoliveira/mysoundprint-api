from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    spotify_client_id: str
    spotify_client_secret: SecretStr
    spotify_redirect_uri: str
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    redis_url: str
    database_url: str

    # Where the OAuth callback sends the browser once the session exists.
    # Left unset, the callback returns the token as JSON instead, which keeps
    # the whole flow testable from /docs while no front end exists.
    # Shared secret for the scheduled collector. Left unset the endpoint
    # refuses every call, so a deployment that forgets it fails closed rather
    # than exposing a route that writes for every user.
    cron_secret: SecretStr | None = None

    frontend_url: str | None = None

    # Comma separated list of origins allowed to call this API from a browser.
    # Falls back to the front end URL plus the usual local dev ports.
    cors_origins: str = ""

    @property
    def allowed_origins(self) -> list[str]:
        if self.cors_origins:
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

        defaults = ["http://localhost:5173", "http://127.0.0.1:5173"]
        if self.frontend_url:
            defaults.append(self.frontend_url.rstrip("/"))
        return defaults


settings = Settings()
