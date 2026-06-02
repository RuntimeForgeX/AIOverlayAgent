# AI Overlay License Server

Node.js backend for premium licensing: user registration, admin approval, RS256 JWT issuance, and `POST /api/activate` for the Python desktop app.

**Stack:** Express · EJS · Prisma · PostgreSQL · `jsonwebtoken` (RS256)

---

## Quick start (local, port 3000)

### 1. PostgreSQL

```bat
cd license-server
docker compose up -d
```

Or use your own Postgres and set `DATABASE_URL` in `.env`.

### 2. Install & configure

```bat
copy .env.example .env
npm install
npm run keys:generate
npm run keys:sync-python
```

`keys:sync-python` copies `keys/public.pem` into `../src/licensing/public_key.py` for offline verify.

### 3. Database

```bat
npm run db:push
npm run db:seed
```

Default admin (from `.env`):

| Field | Value |
|-------|--------|
| Email | `admin@localhost` |
| Password | `admin123` |

### 4. Run server

```bat
npm run dev
```

- Web UI: http://localhost:3000  
- Register user → request license → login as admin → approve  
- User dashboard shows **raw JWT** → paste in Python app → **Activate**

---

## API: `POST /api/activate`

Used by the Python overlay (`LICENSE_ACTIVATE_BASE_URL` + `LICENSE_ACTIVATE_PATH`).

**Request**

```json
{
  "raw_jwt": "<admin-issued raw JWT>",
  "device_hash": "<sha256 hardware fingerprint>",
  "device_info": { "platform": "...", "machine": "...", "node": "..." }
}
```

**Success `200`**

```json
{ "activated_jwt": "<JWT with device_hash claim>" }
```

**Errors**

| Status | Meaning |
|--------|---------|
| 400 | Invalid body or JWT |
| 403 | Revoked or expired |
| 404 | License `jti` not in database |
| 409 | Already bound to another device |

---

## Test with Python app

In project root `.env`:

```env
LICENSE_AUTH=1
LICENSE_ACTIVATE_BASE_URL=http://localhost:3000
LICENSE_GET_LICENSE_URL=http://localhost:3000/request
```

```bat
python main.py
```

Dev without license gate: `LICENSE_AUTH=0`

---

## Generate RSA keys (manual)

```bat
mkdir keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
npm run keys:sync-python
```

Never commit `keys/private.pem`.

---

## Environment variables

See `.env.example`. Important:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection |
| `SESSION_SECRET` | Express session |
| `PRIVATE_KEY_PATH` / `PUBLIC_KEY_PATH` | RS256 keys |
| `PORT` | Default `3000` (matches Python `config.ini`) |
| `JWT_ISSUER` | JWT `iss` claim (`overlay-agent.local`) |
| `USE_MEMORY_SESSION=1` | Skip PG session store (dev only) |

---

## Project structure

```
license-server/
├── prisma/schema.prisma
├── src/
│   ├── app.js
│   ├── server.js
│   ├── config/jwt.js
│   ├── services/jwt.service.js
│   ├── controllers/
│   ├── routes/
│   └── views/
├── keys/                 # gitignored private.pem
└── docker-compose.yml
```

---

## Production notes

- Use **HTTPS** behind a reverse proxy.
- Set strong `SESSION_SECRET` and `cookie.secure: true`.
- Store `private.pem` in secrets manager, not the repo.
- Rate limiting is enabled on `/api/activate`.
- Optional: Nodemailer for approval emails (not wired in v1).

Deploy targets: Railway, Render, Fly.io — run `prisma migrate deploy` and `npm start`.

---

## Licensing flow

1. User registers → requests plan (`15days` / `30days` / `lifetime`).
2. Admin approves → server creates `License` + **raw JWT** (no `device_hash`).
3. User copies raw JWT into desktop app.
4. App calls `POST /api/activate` → server creates `Device`, returns **activated JWT**.
5. App saves `%APPDATA%\...\license.jwt` and verifies offline with public key.
