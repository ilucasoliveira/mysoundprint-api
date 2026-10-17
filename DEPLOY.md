# Deploying MySoundPrint

The same three pieces as locally, each on a free tier: the API on Render,
Postgres on Supabase, Redis on Upstash. This mirrors the setup used for
portfolio-tracker-api.

## 1. Postgres on Supabase

Create a project, then take the connection string from
**Project Settings → Database → Connection string → URI**.

Two things to change in it:

- the driver prefix becomes `postgresql+asyncpg://`
- use the **transaction pooler** host (port `6543`), not the direct one

Then append `?prepared_statement_cache_size=0` to the URI. This is not
optional: `asyncpg` prepares statements by name, the transaction pooler hands
out a different backend connection per transaction, and the prepared statement
is not there any more. The symptom is an intermittent
`InvalidSQLStatementNameError` that never reproduces locally.

Run the migrations once against that URL, from your machine:

```bash
DATABASE_URL="<the supabase url>" poetry run alembic upgrade head
```

## 2. Redis on Upstash

Create a database and copy the connection URL. Upstash requires TLS, so the
scheme is `rediss://` with two S, not `redis://`. A single missing S produces
a connection error that looks like the server is down.

## 3. API on Render

New → Web Service → connect the GitHub repository.

- **Runtime**: Docker (the repository has a Dockerfile)
- **Region**: Oregon, same as the free Postgres tier you may add later
- **Instance type**: Free

Environment variables:

| Key | Value |
| --- | --- |
| `DATABASE_URL` | the Supabase URI, with the asyncpg prefix and the cache parameter |
| `REDIS_URL` | the Upstash URL, `rediss://` |
| `SPOTIFY_CLIENT_ID` | from the Spotify dashboard |
| `SPOTIFY_CLIENT_SECRET` | from the Spotify dashboard |
| `SPOTIFY_REDIRECT_URI` | `https://<your-service>.onrender.com/auth/callback` |
| `JWT_SECRET_KEY` | generate a new one, do not reuse the local value |

## 4. Register the production redirect URI

Back in the Spotify dashboard, add the deployed callback URL to the app's
redirect URIs. Keep the local one as well, so development keeps working.

Spotify requires HTTPS for anything that is not loopback. Render serves HTTPS
by default, so this works, but the value has to match exactly, trailing slash
included.

## 5. After the first deploy

- Open `https://<your-service>.onrender.com/docs`
- Log in through `/auth/login` once, so a user row exists
- Generate the demo snapshots against the deployed instance, or commit the
  ones generated locally

## Things that will bite you

**The free Render instance sleeps.** After 15 minutes without traffic it
spins down, and the next request takes around 50 seconds. Mention this in the
README rather than letting a recruiter think the API is broken.

**Migrations do not run themselves.** The Docker command in
`docker-compose.yml` runs `alembic upgrade head` before Uvicorn, but Render
uses the Dockerfile's `CMD`. Either add the migration to Render's start
command or run it manually after each schema change.

**`requires-python = ">=3.14"`.** Confirm Render's Docker build succeeds with
that version. The Dockerfile pins `python:3.14-slim`, so this is under your
control rather than Render's, which is the reason to deploy with Docker here.
