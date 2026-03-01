# Security Policy

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report via GitHub's Security Advisory feature:

1. Go to **Security → Report a vulnerability** in this repository
2. Include: description, steps to reproduce, potential impact, suggested fix
3. Expected response: 24–48 hours

We will credit reporters in release notes unless they prefer anonymity, and will coordinate responsible disclosure timing.

---

## Authentication

### JWT Strategy

- **Access tokens**: short-lived (15 min), returned in JSON response body, stored in memory on the client — never in `localStorage`
- **Refresh tokens**: longer-lived (7 days), stored in `httpOnly` cookie to prevent JavaScript access
- **Algorithm**: HS256 via `python-jose`; secret loaded from `SECRET_KEY` env var (min 32 chars, high entropy)
- **RBAC**: `admin` and `user` roles enforced at the FastAPI dependency layer (`Depends(require_role(...))`)

### Secret Management

```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Requirements:
- Never commit secrets to version control
- Store in environment variables or a secrets manager (AWS Secrets Manager, HashiCorp Vault, Supabase secrets)
- Rotate `SECRET_KEY` if suspected compromise; this invalidates all active tokens
- Rotate routinely every 90 days in production

---

## API Security

### CORS

Restrict `allow_origins` to known domains in production:

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.traderrr.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

Development: `allow_origins=["http://localhost:3000"]` only.

### Rate Limiting

Not yet implemented. Intended approach: `slowapi` middleware on FastAPI with per-IP limits:

- Global: 200 req/day, 50 req/hour
- Data retrieval: 100 req/hour
- Portfolio mutations: 10 req/hour

Returns `429 Too Many Requests` on breach.

### Input Validation

All request bodies and query parameters are validated by Pydantic schemas at the FastAPI layer before reaching business logic. No manual validation wrappers needed. SQL injection is prevented by SQLAlchemy parameterised queries throughout.

---

## Data Protection

### Sensitive data

- Passwords: hashed with `bcrypt` via `passlib`; plaintext never stored or logged
- Tokens: only the last 8 characters of any token may appear in logs
- Portfolio data: user-scoped at the database level (Row Level Security on Supabase); users cannot access other users' data

### Data in transit

All production traffic must use HTTPS (TLS 1.2+). Nginx or a cloud load balancer handles TLS termination. HSTS header required:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

Recommended additional headers:
```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### Data at rest

- PostgreSQL (Supabase): encryption at rest enabled by default
- Backups: encrypted at source; restricted access; 30-day retention

---

## Logging Security

- Never log full tokens, passwords, or PII
- Log only the last 8 characters of any credential: `****ab12`
- Use structured JSON logging in production for SIEM compatibility
- Retain security-relevant logs (auth failures, admin actions) for 90 days minimum
- Log levels controlled by `LOG_LEVEL` env var; `DEBUG` never enabled in production

---

## Docker & Deployment

- Application containers run as non-root users (`uid 1000`)
- No secrets in Dockerfiles or Docker images; inject via env vars at runtime
- Production images use multi-stage builds; no dev dependencies in final layer
- Health check endpoint: `GET /health` — does not require authentication

---

## Dependency Management

Dependabot is configured for both Python (pip) and JavaScript (pnpm) dependencies. All Dependabot PRs run full CI before merge.

Manual audit:

```bash
# Python
pip-audit                        # or: safety check

# JavaScript
pnpm audit
```

---

## Security Checklist (Pre-Production)

- [ ] Strong `SECRET_KEY` set in environment (≥ 32 chars)
- [ ] CORS restricted to known production domains
- [ ] HTTPS / TLS certificates installed and auto-renewing
- [ ] Rate limiting enabled
- [ ] Structured logging configured; no secrets in logs
- [ ] Supabase Row Level Security policies verified
- [ ] Non-root Docker user confirmed
- [ ] Dependabot alerts reviewed and clear
- [ ] OWASP Top 10 review completed
- [ ] Backup and restore procedure tested

---

## Incident Response

| Severity | Trigger | Action | Timeline |
|----------|---------|--------|----------|
| Critical | Token secret compromise | Rotate `SECRET_KEY`, invalidate all sessions | Immediate |
| Critical | Database breach | Isolate, preserve evidence, notify users | Immediate |
| High | Unauthorised access | Audit logs, revoke affected tokens | < 2 hours |
| Medium | Repeated auth failures | Increase rate limiting, review IP | < 24 hours |
| Low | Dependency vulnerability | Dependabot PR + review | < 1 week |

Report security incidents via the GitHub Security Advisory (see top of this document).
