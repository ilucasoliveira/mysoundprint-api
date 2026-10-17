from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import settings
from app.routers import auth, demo, stats

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
        "email": "lucasoliveirapimentel.dev@gmail.com",
    },
)


# The front end runs on a different origin, so the browser blocks its calls
# until the API says which origins it trusts. Only the ones configured are
# allowed: a wildcard here would let any site on the internet call this API
# with a visitor's token.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/", include_in_schema=False)
async def root():
    """Send anyone landing on the bare domain to the documentation.

    Hidden from the schema: this is navigation, not part of the API.
    """
    return RedirectResponse("/docs")


@app.get("/health", tags=["health"], status_code=200)
async def health_check():
    return {"status": "OK"}


app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(demo.router)
