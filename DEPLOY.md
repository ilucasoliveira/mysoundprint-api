# Deploying MySoundPrint

The same three pieces as locally, each on a free tier: the API on Render,
Postgres on Supabase, Redis on Upstash. This mirrors the setup used for
portfolio-tracker-api.

## 1. Postgres on Supabase

Create a project, then take the connection string from
**Project Settings → Database → Connection string → URI**.

Two things to change in it:

- the driver prefix becomes `postgresql+asyncpg://`
- use the **session pooler** host (port `5432`), not the transaction pooler

The pooler choice matters more than it looks. The transaction pooler hands
out a different backend connection per transaction, which is right for
serverless functions but wrong here: this API runs as a long lived container
with SQLAlchemy's own connection pool, and `asyncpg` prepares statements on
the server with sequential names. Two connections then collide on the same
name and Postgres rejects it with `DuplicatePreparedStatementError`.

The session pooler keeps the connection for the whole session, so prepared
statements behave normally. Appending `?prepared_statement_cache_size=0` is
still worth it as a safety net.

The transaction pooler also resolves over IPv6 by default. On an IPv4-only
network that fails with a name resolution error that looks like a wrong host.

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
- **Region**: pick the one closest to the Supabase region. With the
  database in `ca-central-1` (Montreal), Ohio is the nearest Render
  option. What matters is the distance between the API and the database,
  not between you and either of them.
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
