# HWAX Portal — Architecture

A hub at `hwax.sec.samsung.net` that federates multiple engineering systems behind one
AD-SSO login, then launches users into those systems with their identity propagated.

## The auth seam (why go-live is config-only)

```
                         app/auth/provider.py
  upstream IdP  ──▶  AuthProvider.handle_callback() ──▶  Principal{subject,email,groups}
   (who logs                  ▲                                   │
    the user in)              │                                   ▼   everything below is
                    ┌─────────┴─────────┐              IdP-INDEPENDENT (written once):
                    │ mock_provider     │   AUTH_PROVIDER   • session cookie (HS256)
                    │ saml_provider     │ ◀── env switch     • catalog + tile gating
                    └───────────────────┘                   • downstream launch (RS256/JWKS)
                                                             • the entire React SPA
```

The portal authenticates the user via the **active provider** and normalizes the result to
a `Principal`. Nothing past that point depends on whether login came from the mock or from
real Samsung AD — so switching is an env change (see `GO-LIVE.md`).

## Roles

- **SP toward upstream** (Samsung AD): the portal receives + validates AD's signed SAML
  assertion at `/auth/saml/acs`. Built with `python3-saml`, config/metadata-driven.
- **JWT issuer toward downstream** (linked systems): the portal mints a short-lived (90s),
  audience-scoped **RS256** launch token per system; downstream verifies it against
  `/.well-known/jwks.json`. A downstream **SAML** assertion path is deferred behind the
  `DownstreamTokenIssuer` interface (saml-handoff tiles currently return 501).

## Login flow (mock and SAML are the same shape)

```
SPA "Sign in" ─▶ GET /auth/login ─▶ provider.login_redirect()
                                       mock: 302 → /auth/callback (instant)
                                       saml: 302 → AD SSO (real AuthnRequest)
  ... IdP authenticates the user ...
AD/mock ─▶ /auth/callback (mock) or POST /auth/saml/acs (saml)
        ─▶ provider.handle_callback() → Principal
        ─▶ complete_login(): set httpOnly session + refresh + CSRF cookies
        ─▶ 302 → SPA (return_to)
SPA ─▶ GET /auth/me  (cookie) → user profile
```

Session cookies are httpOnly (SPA never sees the token); CSRF uses a double-submit token on
state-changing routes. The login `state` is a signed JWT round-tripped as SAML RelayState to
bind the response to the attempt (and uses `SameSite=None` in prod so it survives AD's
cross-site POST-back).

## Launch flow (identity → downstream system)

```
tile click
  external-url  → SPA opens system.url directly (no identity propagated)
  jwt-handoff   → POST /systems/{id}/launch
                    → mint RS256 token {aud=system, exp=90s, jti, email, groups}
                    → { mode:auto_post, action:system.url, fields:{token} }
                    → SPA auto-submits a hidden POST form to the system
                    → downstream verifies via JWKS (kid), checks aud/iss/exp, single-use jti
  saml-handoff  → 501 (deferred behind DownstreamTokenIssuer)
```

Replay defense: short TTL + audience restriction (a token for system A fails at system B's
`aud` check) + single-use `jti` recorded in the SQLite token store.

## Components (backend `app/`)

| Area | Modules |
|---|---|
| Auth seam | `auth/provider.py`, `auth/mock_provider.py`, `auth/saml_provider.py`, `auth/saml_sp.py`, `auth/factory.py` |
| Session | `auth/jwt_service.py` (HS256), `auth/cookies.py`, `auth/routes/session.py`, `deps.py` |
| SAML SP / mock IdP | `auth/routes/saml.py`, `auth/routes/mock_idp.py` (dev), `scripts/gen_dev_certs.py` |
| Downstream | `auth/keystore.py` (RS256+JWKS), `auth/downstream.py`, `auth/token_store.py`, `auth/routes/{jwks,launch}.py` |
| Catalog | `catalog/registry.py` (+ `config/systems.yaml`), `catalog/routes.py` |
| Mail | `mail/{base,console,smtp,graph,service}.py`, `mail/routes.py` |

## Config / environments

One `Settings` (`app/config.py`), env-driven. Dev (`.env.example`) runs the whole loop with
zero external deps (mock login, console mail, SQLite). Real domain (`.env.real`) runs prod
single-origin with mock login until SSO is approved. Deliberately deferred, each behind an
interface: downstream SAML-IdP, Redis token store, OIDC upstream.
