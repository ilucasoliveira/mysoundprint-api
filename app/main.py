from fastapi import FastAPI

DESCRIPTION = """Personal listening statistics built on top of the Spotify Web API.

Authenticate with your Spotify account to get insights about your
listening habits: top artists and tracks across time ranges, genre
diversity and how your taste shifts over time.

**Note:** Spotify apps in development mode are limited to a small
allowlist of authenticated users. Use the demo endpoints to explore
the API without a Spotify account."""

app = FastAPI(
    title="MySoundPrint API",
    description=DESCRIPTION,
    version="0.1.0",
    contact={
        "name": "Lucas de Oliveira Pimentel",
        "email": "lucasoliveirapimentel.dev@gmail.com"
    }
)

@app.get("/health", tags=["health"], status_code=200)
async def health_check():
    return {"status": "OK"}