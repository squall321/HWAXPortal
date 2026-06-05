# Drop the Samsung AD metadata here

When the SSO application is approved, save the IdP metadata XML you receive from the
Samsung AD / ADFS / Entra team as:

    samsung_ad_metadata.xml

(this exact filename — it's referenced by `SAML_IDP_METADATA_PATH` in `.env.real`).

Then follow `docs/GO-LIVE.md`:
  1. `AUTH_PROVIDER=saml`
  2. set `SAML_ATTR_EMAIL` / `SAML_ATTR_NAME` / `SAML_ATTR_GROUPS` to the attributes AD emits
  3. restart the backend

Alternatively, instead of a file, set `SAML_IDP_METADATA_URL` to the AD federation metadata
URL (it takes precedence over this file).

Nothing in this directory is secret — IdP metadata + the SP public cert are safe to commit.
The SP **private** key lives in `backend/secrets/` (gitignored).
