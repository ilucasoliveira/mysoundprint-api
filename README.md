# MySoundPrint API

[![CI](https://github.com/ilucasoliveira/mysoundprint-api/actions/workflows/ci.yml/badge.svg)](https://github.com/ilucasoliveira/mysoundprint-api/actions/workflows/ci.yml)

A FastAPI backend that turns your Spotify listening history into personal
statistics: how your top artists and tracks shift across time ranges, how
concentrated your listening is, which eras of music you actually play, and
when you play them.

**Live:** [mysoundprint-api.onrender.com](https://mysoundprint-api.onrender.com)
· [interactive docs](https://mysoundprint-api.onrender.com/docs)
· [try it without an account](https://mysoundprint-api.onrender.com/demo/concentration)

**Front end:** [mysoundprint.vercel.app](https://mysoundprint.vercel.app)
· [repository](https://github.com/ilucasoliveira/mysoundprint-web)

> The free Render instance sleeps after 15 minutes of inactivity, so the
> first request can take up to a minute. Everything after that is fast.

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
6. The API issues its own session JWT. Spotify's tokens stay in the
   database and are never handed to the client.

The `code` is deliberately useless on its own: without the client secret it
cannot be exchanged for anything, which is why the flow does not return the
token directly in the redirect URL.

## Stack

- **FastAPI** + Uvicorn
- **PostgreSQL** for users, tokens and listening history
- **Redis** for OAuth state and response caching
- **SQLAlchemy 2.0** (async) + **Alembic** for migrations
- **httpx** for async calls to the Spotify Web API
- **PyJWT** for session tokens
- **Pydantic Settings** for typed, validated configuration
- **Poetry**, **Docker Compose**, **pytest**

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/health` | no | Liveness check |
| GET | `/auth/login` | no | Redirects to the Spotify consent screen |
| GET | `/auth/callback` | no | Validates `state`, exchanges the code, issues a session JWT |
| GET | `/auth/me` | yes | The authenticated user |
| GET | `/stats/decades` | yes | Which decades your top tracks come from |
| GET | `/stats/concentration` | yes | Distinct artists, tracks per artist, top 3 share |
| GET | `/stats/comparison` | yes | Who entered, dropped, climbed and fell between two time ranges |
| POST | `/stats/history/collect` | yes | Pulls the latest plays into your stored history |
| POST | `/stats/history/collect-all` | secret | Same, for every user; called by the scheduler |
| GET | `/stats/patterns` | yes | Listening by hour, weekday and period, plus streaks |
| GET | `/demo/*` | no | The same four statistics over a stored snapshot |

## Running locally

Requirements: Python 3.14, Poetry and Docker.

```bash
git clone https://github.com/ilucasoliveira/mysoundprint-api.git
cd mysoundprint-api

cp .env.example .env   # then fill in your Spotify credentials

docker compose up -d           # Postgres and Redis
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`.

To run the API in a container as well:

```bash
docker compose --profile full up --build
```

### Spotify credentials

Create an app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard),
select **Web API**, and register `http://127.0.0.1:8000/auth/callback` as the
redirect URI. Spotify rejects `localhost`, so the loopback IP is required.
Copy the Client ID and Client Secret into your `.env`.

Generate the JWT secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Demo snapshots

The `/demo/*` endpoints read stored Spotify responses from `app/demo_data/`.
Generate them from your own account after logging in once:

```bash
poetry run python -m scripts.build_demo_snapshot --user-id 1
```

### Tests and linting

```bash
poetry run pytest -v
poetry run ruff check .
```

The suite covers the statistics functions only. They are pure: they take a
payload and return a result, with no network, database or clock involved,
which is exactly what makes them cheap to test.

Ruff's rule set is pinned in `pyproject.toml` rather than left to the default,
which changes between releases and would turn a dependency bump into a failing
pipeline. FastAPI's `Depends` and friends are declared immutable instead of
switching off B008, since a call in a default argument is the framework's
whole dependency system rather than the mistake that rule exists to catch.

## Scheduled history collection

Spotify returns at most the last 50 plays and cannot page further back, so a
week nobody collects is a week gone for good. A GitHub Actions workflow calls
`POST /stats/history/collect-all` every hour, which turns the history from
something a user has to remember into something that accumulates.

GitHub runs it rather than Render, where cron jobs are a paid feature, and
rather than an in-process scheduler, which would die with a service that
spins down after fifteen minutes without traffic. The call also wakes the
instance, so the first human visitor of the hour meets a warm one.

There is no user to authenticate: the scheduler holds no session, and a
session JWT would expire long before the next run. The route takes a shared
secret in `X-Cron-Secret` instead, compared with `secrets.compare_digest` so
the time the comparison takes says nothing about how much of the secret was
right. An unset or empty `CRON_SECRET` makes the route answer 503 rather than
accepting the empty string, so a deployment that forgets it fails closed.

To enable it: set `CRON_SECRET` on the service, and add the same value as a
repository secret under Settings > Secrets and variables > Actions.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Continuous integration and deployment

`.github/workflows/ci.yml` runs ruff and pytest on every push and pull
request. A push to `main` that passes then calls a Render deploy hook; a pull
request stops at the checks, which is the point of the gate.

This requires Render's own auto-deploy to be **off**, under Settings > Build
and Deploy. Left on, Render deploys on every push whether or not the tests
passed, and the gate is decoration. The hook URL goes in the
`RENDER_DEPLOY_HOOK_URL` repository secret.

Poetry is pinned to the same version in the workflow and in the `Dockerfile`,
because a different one reads `poetry.lock` differently and fails with
"pyproject.toml changed significantly", which is an obscure way to be told
the tool versions disagree.

## A note on Spotify's platform limits

Spotify apps created today start in **development mode**, which allows only a
handful of authenticated users, each added manually to an allowlist by the app
owner, who also needs a Premium account. Extended quota mode is granted to
organizations only.

This means you cannot simply log in with your own Spotify account here. The
`/demo/*` endpoints therefore serve a stored snapshot through the exact same
statistics code, so the project can be explored without an account.

The Web API itself has also been shrinking. Apps registered after November
2024 lost the Audio Features, Audio Analysis, Recommendations and Related
Artists endpoints. A second round in February 2026 removed the bulk artists
endpoint for development mode apps and stripped `genres`, `popularity` and
`followers` from the artist object.

Every statistic here was designed against what the API actually returns
today, verified by inspecting live responses rather than trusting the
reference docs, which still describe fields that no longer arrive.

## Design decisions

**Redis for the OAuth state, not a cookie or a table.** The state is worthless
after a few minutes, so a TTL deletes it with no cleanup job, and `GETDEL`
consumes it atomically, which is what makes a replayed callback fail. The cost
is a hard dependency on Redis in the login path.

**Token expiry is stored as an instant, not a duration.** Spotify returns
`expires_in: 3600`. A duration is meaningless without knowing when it started,
so the addition happens once, on receipt. Answering "is this token still
valid" is then a comparison instead of arithmetic, and the database itself can
answer "whose tokens have expired".

**The refresh response may omit the refresh token.** When it does, it means
"keep the one you have". Overwriting it with `None` would lock the user out
permanently, so the update falls back to the stored value.

**Refresh happens 60 seconds early.** A token valid for three more seconds
passes a naive check and then dies mid request. The margin removes that race.

**The cache key contains the user id.** Without it, one user's top artists
would be served to another. Every parameter that changes the result is in the
key, including `limit`, or a request for 50 items would be answered with a
cached 10.

**429 is retried, but only briefly.** Spotify's `Retry-After` is honoured once,
and only when it is short. A long wait is not worth freezing a request for, so
the error propagates instead.

**Listening history is collected, not fetched.** The recently played endpoint
returns at most 50 plays and cannot be paginated into the past, so any real
history has to be accumulated. Duplicates are prevented twice over: the `after`
cursor asks Spotify only for what is new, and a unique constraint on
`(user_id, played_at)` with `ON CONFLICT DO NOTHING` means the database refuses
a duplicate even if two collectors run at once.

**Timestamps are stored in UTC and converted on read.** "When do I listen" is a
question about local time, so the timezone is a query parameter rather than a
stored assumption. `zoneinfo` reads the IANA database from the operating
system, which Windows and slim Docker images do not ship, so `tzdata` is a
hard dependency rather than a convenience.

**The scheduled collector authenticates with a secret, not a token.** Every
other write on this API belongs to a user and carries their JWT. That one has
no user behind it and runs unattended, so it takes a shared secret instead,
and the comparison is constant time. The endpoint is in the public schema
rather than hidden: the secret is the protection, and a route nobody can see
is not a route nobody can find.

**Statistics are pure functions.** They take a payload and return a result.
That is what lets the demo endpoints reuse them untouched, and what makes the
tests run without any infrastructure.

## Known limitations

- `release_date` is the album's date, not the recording's, so remasters and
  re-recordings are counted in the decade they were reissued.
- Concentration counts only the primary artist of each track, so the shares
  add up to 100% at the cost of under-crediting featured artists.
- The demo snapshots are real data from the author's account.

## Roadmap

- [x] OAuth2 authorization code flow with CSRF protection
- [x] Persist users and tokens, issue a session JWT
- [x] Automatic access token refresh
- [x] Spotify API client with Redis caching and 429 handling
- [x] Statistics endpoints
- [x] Demo mode and tests
- [x] Deployment
- [x] Scheduled history collection
- [x] React front end
- [x] Continuous integration and gated deployment

## License

MIT
