# MySoundPrint API

A FastAPI backend that turns your Spotify listening history into personal
statistics: top artists and tracks across time ranges, genre diversity and
how your taste shifts over time.

> **Work in progress.** The OAuth2 layer is done. Statistics endpoints are
> being built.

## How the authentication works

This project implements the OAuth2 Authorization Code Flow by hand, without
an auth library, so every step is explicit:

1. `GET /auth/login` builds the Spotify authorization URL and redirects the
   browser to it, along with a random `state` value stored in Redis with a
   5 minute TTL.
2. The user grants access on Spotify's own consent screen. The app never
   sees their password.
3. Spotify redirects back to `GET /auth/callback` with a short lived,
   single use `code` and the original `state`.
4. The `state` is validated with an atomic `GETDEL`, so a replayed callback
   is rejected. This protects against CSRF.
5. The `code` is exchanged for an `access_token` and a `refresh_token` in a
   server to server POST, authenticated with HTTP Basic. The client secret
   never touches the browser.

The `code` is deliberately useless on its own: without the client secret it
cannot be exchanged for anything, which is the reason the flow does not
return the token directly in the redirect URL.

## Stack

- **FastAPI** + Uvicorn
- **Redis** for short lived OAuth state
- **PostgreSQL** for users and tokens
- **httpx** for async calls to the Spotify Web API
- **Pydantic Settings** for typed, validated configuration
- **Poetry** for dependency management
- **Docker Compose** for local services

## Running locally

Requirements: Python 3.14, Poetry and Docker.

```bash
git clone https://github.com/ilucasoliveira/mysoundprint-api.git
cd mysoundprint-api

cp .env.example .env   # then fill in your Spotify credentials

docker compose up -d
poetry install
poetry run uvicorn app.main:app --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`.

### Spotify credentials

Create an app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard),
select **Web API**, and register `http://127.0.0.1:8000/auth/callback` as the
redirect URI. Copy the Client ID and Client Secret into your `.env`.

Generate the JWT secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## A note on Spotify's platform limits

Spotify apps created today start in **development mode**, which allows only a
handful of authenticated users, each added manually to an allowlist by the app
owner, who also needs a Premium account. Extended quota mode is granted to
organizations only.

This means you cannot simply log in with your own Spotify account here. The
API is therefore built with a demo mode that serves a stored snapshot through
the same endpoints, so the project can be explored without an account.

Apps registered after November 2024 also lost access to the Audio Features,
Audio Analysis, Recommendations and Related Artists endpoints. All statistics
in this project are derived from top items and recently played tracks.

## Endpoints

| Method | Path             | Description                                         |
| ------ | ---------------- | --------------------------------------------------- |
| GET    | `/health`        | Liveness check                                      |
| GET    | `/auth/login`    | Redirects to the Spotify consent screen             |
| GET    | `/auth/callback` | Validates `state` and exchanges the code for tokens |

## Roadmap

- [x] OAuth2 authorization code flow with CSRF protection
- [ ] Persist users and tokens, issue a session JWT
- [ ] Automatic access token refresh
- [ ] Spotify API client with Redis caching and 429 handling
- [ ] Statistics endpoints
- [ ] Demo mode, tests and deployment

## License

MIT
