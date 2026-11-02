# CI/CD banas.dev

The live HTML and images matched `main` at `ce6592e` when CI/CD was added.
Cloudflare Rocket Loader modifies the public HTTP response; its injected script
is not source code to copy into Git. Weather JSON changes on the VPS, independently
of Git, and is intentionally excluded from release archives.

## Pipeline

`.github/workflows/ci-cd.yml` checks every push and PR: Python syntax, HTML local
assets and anchors, inline JavaScript syntax, collector storage, release handling
and rollback. It packages only checked source and uploads a seven-day artifact.
After a push to `main`, or manual execution on `main`, a dependent production job
deploys that exact artifact. Failed checks prevent deployment. PRs cannot deploy.

Like `ai-resume-tailoring-platform`, deployment uses a dedicated forced-command
SSH key, pinned server host identity, serialized production jobs and a server lock.
A static website does not need a Docker build or registry. Releases are immutable
ZIP archives identified by commit and SHA-256; no code from an archive is executed
by the receiver. Both SSH wrapper and receiver are installed once as root-owned
files and are not updated by subsequent releases. Changes to those files require
an explicit server installation.

Actions checks that the current live SHA is an ancestor of the requested release,
preventing queued older runs from replacing a newer release. Deployment prepares
a separate directory, validates archive names/size/digest/revision, then atomically
switches `current`. A loopback Nginx health check verifies exact revision, HTML
checksum and readable weather JSON. A failed health check restores the prior
symlink and checks its health. Deployments keep previous releases on disk; do not
remove the current or previous release when manually cleaning disk space.

## Server layout

- `/var/lib/banasdev/releases/`: versioned HTML, assets and collector source.
- `/var/lib/banasdev/current`: atomic pointer to the active release.
- `/var/lib/banasdev/previous`: path to the prior successful release.
- `/var/lib/banasdev-weather/`: isolated weather JSON, SQLite database and log
  for the unprivileged collector. Public JSON paths are symlinks into this directory.
- `/cytrus/`: legacy data and HTTP redirect. Preserve it during migration; do
  not grant the collector write access here.
- `/etc/banasdev/deploy.json`: root-owned configuration, copied from
  `deploy.example.json` (mode 600).
- `/usr/local/sbin/banasdev-deploy`: installed copy of `deploy.py` (root, 755).
- `/usr/local/bin/banasdev-cd-ssh`: installed copy of `ssh-command.sh` (root, 755).

The public HTTPS virtual host keeps TLS and Cloudflare settings and uses
`root /var/lib/banasdev/current/public;`. Add `nginx-loopback.conf` to Nginx for
health checks; its listener is bound only to loopback. Test `nginx -t` before
reload. The public root contains no Python, deployment tooling, Git or SQLite.
The public virtual host configuration is tracked in `nginx-public.conf`. It
redirects HTTP (including requests forwarded over HTTPS by Cloudflare) and
`www` to `https://banas.dev`, and sends a canonical `Link` header for `/` and
`/index.html`. Install it as `/etc/nginx/sites-available/default`; validate with
`nginx -t` before reloading. These rules persist across application releases.

The hosting provider also serves plain HTTP for the apex domain directly from
`/cytrus/index.html`, bypassing this Nginx. That legacy file is now the
`legacy-http-redirect.html` redirect page, with an instant meta refresh and a
canonical URL pointing to `https://banas.dev/`. Keep the legacy redirect outside
the release pipeline; do not copy it into the HTTPS release's public directory.
Weather data and collector files in `/cytrus` remain unchanged.

### Collector privilege separation — operator migration required

`collector.cron` is an `/etc/cron.d` file, **not a user crontab**. Neither the
collector nor its data directory should be owned/run by root. Provision a
dedicated account without login or sudo access (skip useradd if it already exists):

```bash
useradd --system --user-group --no-create-home --shell /usr/sbin/nologin banasdev-weather
# Substitute the verified Nginx worker group if it is not www-data.
install -d -o banasdev-weather -g www-data -m 0750 /var/lib/banasdev-weather
```

Migration order, during a planned maintenance window:

1. Back up data, deployment config and cron. Remove **only the two old collector
   entries** from root's crontab; preserve unrelated jobs. Wait for already-running
   collectors to finish before copying SQLite. If SQLite uses WAL, use its backup
   mechanism or preserve the complete consistent database, not just the main file.
2. Copy (do not delete the originals) `data.json`, `history.json`, `weather.json`,
   `weather_history.db` and the log into the isolated directory. Give the collector
   ownership of those copies; keep SQLite/log private (0600), JSON readable by the
   Nginx worker (0644). Directory write access is necessary for atomic export and
   SQLite journal files. **Do not chown -R /cytrus** or grant write access there.
3. Set `data_dir` in root-owned `/etc/banasdev/deploy.json` to
   `/var/lib/banasdev-weather`. Verify the service can read/traverse the release
   path, but cannot write releases, `current`, deployment config, cron or SSH keys.
   Verify Nginx can traverse the data directory and read all three JSON files.
4. Publish a **new** release using the existing deployment procedure. It creates
   symlinks into the new directory. Reusing an already-existing release directory
   does not update its symlinks. Verify both origin and public JSON responses.
5. Before activating cron, test each mode as the service account (these commands
   fetch real data, so run them only as an authorized operator):

   ```bash
   runuser -u banasdev-weather -- /usr/bin/env BANASDEV_DATA_DIR=/var/lib/banasdev-weather /usr/bin/python3 /var/lib/banasdev/current/fetch_weather.py --weather-only
   runuser -u banasdev-weather -- /usr/bin/env BANASDEV_DATA_DIR=/var/lib/banasdev-weather /usr/bin/python3 /var/lib/banasdev/current/fetch_weather.py --air-only
   install -o root -g root -m 0644 deploy/collector.cron /etc/cron.d/banasdev-weather
   ```

Old releases still link to `/cytrus`. For rollback, plan an operator-reviewed
relink of their three public JSON links to the new data directory; do not restart
the root collector or delete either database. Do not blindly restore a legacy
root crontab as a recovery procedure. New permissions, migration and cron
installation are **not** applied by CI/CD or by editing these repository files.

### Browser security policy and public headers

The HTML contains a hash-based CSP, allowing only its exact inline JS/CSS and
same-origin assets. `data-cfasync="false"` keeps application scripts out of Rocket
Loader rewriting. After intentional inline changes run:

```bash
python3 scripts/security_policy.py --write
python3 scripts/check_site.py
```

CI rejects stale hashes. Do not enable an HTML/script rewriting optimizer at
the edge without checking CSP violations. Third-party injected analytics are not
allowlisted; review/disable such injection in Cloudflare rather than weakening
script-src with unsafe-inline or unsafe-eval. No Cloudflare settings were changed.

`nginx-public.conf` adds framing protection (CSP frame-ancestors and DENY),
nosniff, an explicit referrer policy, and staged **host-only HSTS max-age=300**.
The hash policy in HTML and header policy are complementary; meta CSP cannot
enforce frame-ancestors. Both the server and canonical-page location declare
headers, because Nginx location add_header overrides parent header inheritance.

Install the configuration only after backing up the active virtual host and
validating its paths/certificates with `nginx -t`. Check `/`, `/index.html`,
an asset and a 404 **through public Cloudflare**, not just origin. Remove any
edge rule overwriting HSTS with max-age=0 or removing the other headers. After
successful HTTPS monitoring, increase max-age gradually; do not add
includeSubDomains/preload without verifying every subdomain. This activation
requires an operator and was not performed here.

Before switching the Nginx root, seed `current/public` from the existing live
HTML/assets with `revision.txt` containing the matching full `main` commit SHA.
Use the collector with `BANASDEV_DATA_DIR` support in this bootstrap release.
This initial snapshot is a migration baseline; subsequent releases come solely
from the tested CI artifact. Back up Nginx configuration and root crontab first.
Keep `/cytrus` intact so the previous server configuration can be restored.

## Restricted account and GitHub configuration

Create `banasdev-deploy` with a locked password, a regular shell for the forced
command, and no supplementary privileged groups. Its `.ssh/authorized_keys`
(mode 600) contains only:

```text
restrict,command="/usr/local/bin/banasdev-cd-ssh" ssh-ed25519 PUBLIC_KEY
```

Install root-owned `/etc/sudoers.d/banasdev-cd` (440), validate with `visudo -cf`:

```text
banasdev-deploy ALL=(root) NOPASSWD: /usr/local/sbin/banasdev-deploy
```

Set repository secrets `VPS_HOST` (origin, not Cloudflare proxy), `VPS_PORT`,
`VPS_USER=banasdev-deploy`, `VPS_SSH_KEY` and `VPS_KNOWN_HOSTS`. Obtain host key
from `/etc/ssh/ssh_host_ed25519_key.pub`, not an unverified network scan. Use
`[hostname]:port` for a nonstandard port. Create GitHub environment `production`
and restrict deployments to `main`. Never reuse CVTailor's deployment key.

The separate `Check banas.dev deployment connection` workflow verifies SSH from
an actual GitHub runner and confirms that arbitrary commands are rejected. It
runs on the initial setup branch and can also be run manually after merging.

## Manual recovery

The server automatically rolls back a failed release. To intentionally revert a
healthy release, use a Git revert merged into `main`; it preserves SHA ancestry.
For emergency server recovery, inspect `/var/lib/banasdev/previous`, then as root
atomically replace `current` with a symlink to that directory. Check the loopback
revision, HTML and JSON and inspect collector logs. This changes code, not the
database. Restoring old Nginx or cron configuration is a separate migration
decision; do not restore root execution of the collector. Run `nginx -t` before
reloading a reviewed configuration.

## Local validation

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_site.py  # requires Node.js on PATH
python3 scripts/check_nginx.py  # optional: requires Nginx and OpenSSL; isolated instance only
python3 scripts/browser_smoke.py  # optional: requires Playwright Chromium
python3 -m compileall -q fetch_weather.py scripts deploy tests
bash -n deploy/ssh-command.sh
```
