# GO-LIVE — switching from mock login to real Samsung AD SSO

The portal runs on **mock login** today so it can be deployed and demoed at
`hwax.sec.samsung.net` before the SSO application is approved. Switching to real AD is a
**config change, not a code change** — this file is the exact checklist.

The reason it's config-only: the entire system is built against one seam,
`app/auth/provider.py::AuthProvider → Principal`. The `mock` and `saml` providers both
produce the same `Principal`; everything downstream (session, catalog, launch, the SPA)
never knows which one ran. This was proven end-to-end in dev with a real signing mock IdP
(see `docs/architecture.md`).

## What you give Samsung AD (so they can register the portal as an SP)

1. The **SP metadata**, served live at:
   ```
   https://hwax.sec.samsung.net/auth/saml/metadata
   ```
2. The **ACS URL** (where AD posts the signed response):
   ```
   https://hwax.sec.samsung.net/auth/saml/acs
   ```
3. The **SP EntityID**: `https://hwax.sec.samsung.net/sp`

The SP signing cert is in `backend/config/saml/sp.crt` (regenerate a prod pair with
`backend/scripts/gen_dev_certs.py` or your PKI; keep the private key in `backend/secrets/`).

## What you get back from Samsung AD

- The **IdP metadata** (an XML file or a URL).
- The list of **attributes** the IdP releases (which claim carries the employee email,
  display name, and group membership) and the **NameID** format.

## The switch (edit `backend/.env`)

```diff
- AUTH_PROVIDER=mock
+ AUTH_PROVIDER=saml

  # point at the AD metadata — EITHER a file you drop in:
  SAML_IDP_METADATA_PATH=config/saml/prod/samsung_ad_metadata.xml
  # OR a live URL (uncomment, takes precedence over the path):
+ # SAML_IDP_METADATA_URL=https://<ad-host>/federationmetadata/2007-06/FederationMetadata.xml

  # map AD's actual attribute names → the portal's Principal fields:
  SAML_ATTR_EMAIL=<the attribute AD emits for email>
  SAML_ATTR_NAME=<the attribute AD emits for display name>
  SAML_ATTR_GROUPS=<the attribute AD emits for group membership>
```

Then restart the backend. That's it — no code edits.

### Step by step
1. Drop the AD metadata file at `backend/config/saml/prod/samsung_ad_metadata.xml`
   (or set `SAML_IDP_METADATA_URL`).
2. Set `AUTH_PROVIDER=saml`.
3. Set the three `SAML_ATTR_*` names to match what AD releases.
4. Confirm `PUBLIC_BASE_URL=https://hwax.sec.samsung.net` (so the derived ACS/SLS URLs and
   SAML `Destination` validation use the real host).
5. Restart. Visit the portal → "Sign in" now bounces to the real Samsung AD login.

## Verify after the switch
- `GET /auth/saml/metadata` returns the SP metadata (200).
- Click "Sign in with Samsung AD" → you land on the real AD login → back at the portal home,
  signed in as **your** AD identity (not the demo user).
- `GET /auth/me` shows your real email + AD groups.

## Notes
- The portal is an **SP** toward AD (validates AD's signed assertion) and a **JWT issuer**
  toward downstream systems (RS256 via `/.well-known/jwks.json`). Those are independent;
  the AD switch does not touch downstream launch.
- `SAML_MOCK_IDP_ENABLED=false` in prod (it is dev-only and never mounted when `APP_ENV=prod`).
- If AD requires the SP to sign AuthnRequests or wants the assertion encrypted, that is a
  config/security-block change in `app/auth/saml_sp.py` `security` settings — still no flow change.
