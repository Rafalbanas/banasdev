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
- `/cytrus/`: persistent weather JSON, SQLite database and log. Existing data is
  retained; the release's public JSON paths are symlinks to this directory.
- `/etc/banasdev/deploy.json`: root-owned configuration, copied from
  `deploy.example.json` (mode 600).
- `/usr/local/sbin/banasdev-deploy`: installed copy of `deploy.py` (root, 755).
- `/usr/local/bin/banasdev-cd-ssh`: installed copy of `ssh-command.sh` (root, 755).

The public HTTPS virtual host keeps TLS and Cloudflare settings and uses
`root /var/lib/banasdev/current/public;`. Add `nginx-loopback.conf` to Nginx for
health checks; its listener is bound only to loopback. Test `nginx -t` before
reload. The public root contains no Python, deployment tooling, Git or SQLite.
Replace only the two existing collector cron entries with `collector.cron`;
keep other cron tasks. `BANASDEV_DATA_DIR` keeps SQLite and JSON outside releases;
local development without it retains the previous behavior.

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
database. Restoring the old Nginx configuration and old crontab returns the site
to `/cytrus`; run `nginx -t` before reloading.

## Local validation

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_site.py  # requires Node.js on PATH
python3 -m compileall -q fetch_weather.py scripts deploy tests
bash -n deploy/ssh-command.sh
```
