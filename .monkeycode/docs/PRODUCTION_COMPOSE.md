# Production Compose

## Scope and entry point

- Run commands from the repository root. The selected file is `docker-compose.yml`.
- One published application entry: host `8000` -> `web:80` (Nginx).
- Nginx serves the SPA and forwards `/api` and `/api/*`, including query strings, unchanged to `api:8000`. `/health` also reaches the API.
- `api`, PostgreSQL, Redis and Chroma have no host port mappings. `expose: 8000` documents the API's container port.
- This is the application's internal API reverse proxy. There are no platform tunnels, external upstreams or forwarding services.
- `docker-compose.dev.yml` and `Dockerfile.frontend` are outside this production path. Select `-f docker-compose.yml` explicitly.

## Build and artifact contract

1. `Dockerfile` stage `frontend-builder` retains the existing `npm ci` and `npm run build` flow in `/frontend`; its artifact is `/frontend/dist`.
2. Target `web` copies that artifact into `/usr/share/nginx/html` and `nginx.production.conf` into `/etc/nginx/conf.d/default.conf`. The official Nginx image supplies its foreground startup command.
3. Target `api` copies the Python virtual environment from `builder`, retains the existing migration/Uvicorn startup, and copies the same SPA artifact after `COPY . .` so host files cannot overwrite it.
4. Compose selects targets `web` and `api`. Both reuse the existing frontend build stage/cache; host `dist` is not a prerequisite. No development server runs in production.

The frontend manifest, lockfile, TypeScript checks and build configuration remain owned by the frontend team. Their build must pass before either image is deliverable.

## Required configuration

- `POSTGRES_PASSWORD`: explicitly required by both database and API configuration via `${POSTGRES_PASSWORD:?...}`. Empty and missing values block Compose interpolation. There is no default password.
- The same raw password is inserted into the PostgreSQL URL. Use at least 32 URL-safe characters from `A-Z a-z 0-9 _ -`; 64 independently random hex characters are suitable. Reserved URL characters need separate encoding support and are outside this configuration contract.
- `APP_SECRET_KEY`: explicitly required via `${APP_SECRET_KEY:?...}`. Supply a separate strong, stable random secret of at least 32 characters. Changing it can invalidate existing authentication tokens.
- `INITIAL_ADMIN_PASSWORD`: explicitly set a strong bootstrap password on the first start with an empty users table. Production initialization raises an error when it is absent. Existing users are preserved; this variable does not reset their passwords. Compose leaves it optional for existing databases.
- `.env.example` contains blank secret placeholders. Its development/SQLite settings are for local application use; Compose explicitly sets production mode, disables debug, and builds the PostgreSQL URL.
- Supply actual values through an operator-controlled secret mechanism or exported shell variables. The commands below use `--env-file /dev/null` to disable implicit `.env` loading. Exported variables must stay in the same operator shell for subsequent commands.
- Do not print environment dumps, enable shell tracing, or publish rendered Compose configuration containing real values. `config --quiet` checks configuration without rendering secrets.
- An existing PostgreSQL volume keeps its existing database password. Changing the environment alone does not rotate that password; coordinate database-side rotation and application configuration.

## Operator preflight

This subshell validates already exported values without printing them, loading an environment file, starting Docker, or contacting a database. It requires an already installed Docker CLI with Compose.

```bash
(
  set -eu
  : "${POSTGRES_PASSWORD:?Export POSTGRES_PASSWORD first}"
  : "${APP_SECRET_KEY:?Export APP_SECRET_KEY first}"
  case "$POSTGRES_PASSWORD" in
    *[!A-Za-z0-9_-]*) printf '%s\n' 'POSTGRES_PASSWORD must be URL-safe' >&2; exit 1 ;;
  esac
  test "${#POSTGRES_PASSWORD}" -ge 32 || { printf '%s\n' 'POSTGRES_PASSWORD must have at least 32 characters' >&2; exit 1; }
  test "${#APP_SECRET_KEY}" -ge 32 || { printf '%s\n' 'APP_SECRET_KEY must have at least 32 characters' >&2; exit 1; }
  docker compose --env-file /dev/null -f docker-compose.yml config --quiet
)
```

For first deployment with an empty users table, also validate the bootstrap credential:

```bash
(
  set -eu
  : "${INITIAL_ADMIN_PASSWORD:?Export INITIAL_ADMIN_PASSWORD for first startup}"
  test "${#INITIAL_ADMIN_PASSWORD}" -ge 16 || { printf '%s\n' 'Use a bootstrap password of at least 16 characters' >&2; exit 1; }
)
```

These length/character checks are deployment policy; Compose itself enforces presence/nonempty values for the two required secrets. The application determines whether first-user initialization is needed. Prepare the `./data` bind mount with write permissions for the built API image's `appuser` before startup.

## Authentication without a login screen

Production keeps `enable_auth` enabled. The SPA currently has no login flow; unauthenticated requests to protected APIs return 401. Serving its static files successfully is insufficient to declare the authenticated UI ready.

The existing HTTP integration contract is `POST /api/v1/auth/login` with operator-provisioned user credentials, followed by the issued access token in `Authorization: Bearer ...`. The frontend reads `auth_token` from browser local storage for its API client and fetch-based streams. This is a contract for a separately approved same-origin authentication handoff, not an implemented login flow in this change.

A suitable follow-up is a trusted same-origin authentication portal/session adapter: authenticate each user, issue or exchange for application-valid user tokens, implement expiry/refresh/logout, then enter the SPA. Native browser WebSockets need a server-issued, short-lived `access_token` cookie because the existing WebSocket handler accepts that cookie and browsers cannot attach arbitrary Authorization headers. Use Secure/HttpOnly cookies with an explicit SameSite policy and origin/CSRF controls; the current login endpoint's JSON token response alone does not establish this cookie handoff.

Keep this integration as an explicit production UI release prerequisite. Do not disable authentication, embed admin credentials in the SPA, or inject a shared admin Authorization header in Nginx. This deployment patch implements no token issuance or login changes. Public production credential transport also requires trusted HTTPS termination; this Compose entry is HTTP and includes no TLS provisioning or platform tunnel.

## API, SSE and WebSocket routing

- Frontend API base `/api/v1` matches `app.include_router(..., prefix="/api/v1")`. Nginx preserves the complete path and query via `$request_uri`; no prefix stripping occurs. The upstream service name and port match Compose `api` and Uvicorn `8000`.
- `/api/v1/sessions/{id}/chat` returns `text/event-stream`. API proxy buffering and caching are disabled, gzip is disabled under `/api/`, and read/send timeouts are 3600 seconds. Authorization headers are forwarded normally.
- `/api/v1/ws/...` routes match the same `/api/` location. HTTP/1.1 and conditional Upgrade/Connection headers support the upgrade; ordinary HTTP requests use `Connection: close`. Cookie forwarding uses Nginx defaults.
- Docker's internal DNS resolver `127.0.0.11` resolves the fixed `api` service through a variable upstream. Replacement API containers can be resolved again without restarting Nginx.
- `/assets/` serves actual files with immutable caching and returns 404 for missing assets; SPA routes fall back to `index.html` with revalidation.
- The web healthcheck uses GET, matching the backend's GET `/health`. Existing probes establish HTTP reachability; the backend may return HTTP 200 with `status: degraded`, so deployment acceptance must inspect the health response body as well.
- Backend proxy-trust configuration remains unchanged. Verify client-IP/rate-limit behavior and HTTPS forwarding as part of the separately approved ingress integration.

## Later operator acceptance

The following commands are for a later authorized build/start after preflight, data-directory preparation and authentication/HTTPS integration. They were not executed during this change.

```bash
docker compose --env-file /dev/null -f docker-compose.yml build web api
docker compose --env-file /dev/null -f docker-compose.yml run --rm --no-deps web nginx -t
docker compose --env-file /dev/null -f docker-compose.yml up -d
```

Confirm the SPA and hashed assets load, deep links work, missing assets return 404, only the web port is published, and `/health` reports healthy dependencies. With per-user credentials, verify API success, incremental SSE delivery and WebSocket 101 upgrade. Also verify unauthenticated/expired credentials remain rejected.

## Validation boundary

This change is checked through local static configuration inspection only. Docker and Nginx executables are absent in the current environment. Compose's own interpolation validation, `nginx -t`, image builds, migrations, container startup, authenticated browser flows and live SSE/WebSocket traffic remain unverified. No installation, Docker startup, deployment, commit or push is performed.
