# Offline package bundle

Carry HWAX to an air-gapped server with **no internet and no sudo**. HWAX needs far less than a
full stack: the SPA is pre-built (`frontend/dist`) and every Python dep is baked into `portal.sif`,
so the only host prerequisite is **apptainer** — installed here as a **local extracted binary**.

## Layout

```
infra/packages/
├── deb/    apptainer_<ver>_<arch>.deb   # apptainer (extracted no-sudo by bootstrap.sh)
└── sif/    portal.sif, nginx.sif        # pre-built images (run directly, no rebuild)
frontend/dist/                            # pre-built SPA (ships in the bundle as-is)
```

The blobs (`deb/`, `sif/`, `*.deb`, `*.sif`, `dist/`) are **gitignored** — only this README is tracked.

## Build the bundle (ONLINE machine)

```bash
./infra/scripts/build.sh                 # produce portal.sif + nginx.sif
pnpm --dir frontend build                # produce frontend/dist  (or it's built by start.sh)
./infra/scripts/download-packages.sh     # collect apptainer .deb + .sif into infra/packages/
tar -czf hwax-offline-bundle.tar.gz infra/packages frontend/dist
```

## Install (air-gapped Ubuntu 24.04 server)

```bash
tar -xzf hwax-offline-bundle.tar.gz -C <repo>     # onto a git checkout of HWAXPortal
cd <repo>
./infra/scripts/bootstrap.sh --offline            # extract apptainer locally (no sudo)
cp infra/packages/sif/*.sif infra/apptainer/       # stage the pre-built images
cp infra/.env.example infra/.env                   # set ports / PUBLIC_BASE_URL / SESSION_SECRET
./infra/scripts/start.sh                           # build + SPA both skip → boots
```

## Notes

- The extracted apptainer is **not setuid** → it runs via **unprivileged user namespaces**
  (Ubuntu 24.04 default = on). If a hardened host disables them, install the same cached .deb
  with sudo instead: `sudo dpkg -i infra/packages/deb/apptainer_*.deb`.
- Offline = **run** the pre-built `.sif`. **Rebuilding** an image from its `.def` (apt + pip in
  `%post`) needs network or a local mirror — the bundle ships the `.sif` so no rebuild is needed.
