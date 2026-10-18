import asyncio

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db
from app.routers import auth, demo, stats
from app.services.redis_client import redis_client

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


PROBE_TIMEOUT_SECONDS = 3


@app.get("/health", tags=["health"], status_code=200)
async def health_check() -> dict:
    """Liveness: is this process running and able to answer at all.

    It touches nothing external on purpose. A platform health check pointed at
    a route that fails when the database blinks will kill and restart the
    container, turning a ten second outage in a dependency into a restart loop.
    Whether the dependencies are reachable is a different question, and it has
    its own route below.
    """
    return {"status": "OK"}


async def _probe(check) -> str:
    """Run one dependency check and reduce it to a single word.

    Everything is caught deliberately. The job here is to report a state, not
    to propagate a failure: an exception escaping would take the whole response
    with it and say nothing about the other dependency.
    """
    try:
        await asyncio.wait_for(check, timeout=PROBE_TIMEOUT_SECONDS)
    except TimeoutError:
        return "timeout"
    except Exception:
        return "unreachable"
    return "ok"


@app.get("/health/ready", tags=["health"])
async def readiness_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Readiness: can this instance actually serve a request.

    Answers 503 when a dependency is down, which is the only thing an uptime
    monitor can act on. A 200 carrying `"database": "unreachable"` in the body
    reads as healthy to every monitor there is, and the alert never fires.

    The two probes run together rather than in sequence, so a stalled
    dependency costs the timeout once instead of twice.
    """
    database, cache = await asyncio.gather(
        _probe(db.execute(text("SELECT 1"))),
        _probe(redis_client.ping()),
    )

    ready = database == "ok" and cache == "ok"
    return JSONResponse(
        {
            "status": "ok" if ready else "degraded",
            "database": database,
            "cache": cache,
        },
        status_code=200 if ready else 503,
    )


app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(demo.router)
