#!/usr/bin/python3
"""Root-owned receiver for bounded release archives over forced-command SSH."""
import ast
import fcntl
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from urllib.request import urlopen
import zipfile

MAX_BYTES = 16 * 1024 * 1024
FILES = {
    "public/index.html", "public/robots.txt", "public/favicon.png",
    "public/cv_photo.jpg", "public/cv_photo.webp", "public/cv_photo2.jpg",
    "public/cv_photo2.webp", "public/revision.txt", "fetch_weather.py",
}
LIVE_FILES = ("data.json", "history.json", "weather.json")


def switch(current, destination):
    temporary = current.with_name("current.next")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(destination)
    temporary.replace(current)


def healthy(config, revision, index_digest):
    try:
        base = config["health_url"].rstrip("/")
        with urlopen(base + "/revision.txt", timeout=3) as response:
            if response.read(100).decode().strip() != revision:
                return False
        with urlopen(base + "/index.html", timeout=3) as response:
            if hashlib.sha256(response.read(MAX_BYTES)).hexdigest() != index_digest:
                return False
        for name in LIVE_FILES:
            with urlopen(base + "/" + name, timeout=3) as response:
                json.loads(response.read(MAX_BYTES))
        return True
    except (OSError, ValueError):
        return False


def deploy(config, revision, digest, stream):
    if not re.fullmatch(r"[a-f0-9]{40}", revision) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Invalid revision or archive digest")
    state = Path(config["state_dir"])
    state.mkdir(parents=True, exist_ok=True)
    with (state / "deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        payload = stream.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES or hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError("Archive size or digest mismatch")
        releases = state / "releases"
        releases.mkdir(exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="staging-", dir=releases))
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                entries = archive.infolist()
                if len(entries) != len(FILES) or {entry.filename for entry in entries} != FILES:
                    raise ValueError("Unexpected archive entries")
                if sum(entry.file_size for entry in entries) > MAX_BYTES:
                    raise ValueError("Expanded archive too large")
                for entry in entries:
                    target = staging / entry.filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # Never extract symlinks, archive modes or untrusted paths.
                    target.write_bytes(archive.read(entry))
                    target.chmod(0o644)
            if (staging / "public/revision.txt").read_text().strip() != revision:
                raise ValueError("Archive revision mismatch")
            ast.parse((staging / "fetch_weather.py").read_text())
            for name in LIVE_FILES:
                (staging / "public" / name).symlink_to(Path(config["data_dir"]) / name)
            staging.chmod(0o755)
            (staging / "public").chmod(0o755)
            release = releases / (revision + "-" + digest[:16])
            if release.exists():
                shutil.rmtree(staging)
            else:
                staging.rename(release)
            current = state / "current"
            previous = current.resolve(strict=True) if current.is_symlink() else None
            index_digest = hashlib.sha256((release / "public/index.html").read_bytes()).hexdigest()
            switch(current, release)
            try:
                for _ in range(config.get("health_attempts", 10)):
                    if healthy(config, revision, index_digest):
                        break
                    time.sleep(config.get("health_interval", 2))
                else:
                    raise RuntimeError("Origin health check failed")
                # Persist rollback metadata before reporting success.
                if previous and previous != release:
                    (state / "previous").write_text(str(previous) + "\n")
            except BaseException:
                if previous:
                    switch(current, previous)
                    old_revision = (previous / "public/revision.txt").read_text().strip()
                    old_digest = hashlib.sha256((previous / "public/index.html").read_bytes()).hexdigest()
                    if not healthy(config, old_revision, old_digest):
                        print("ROLLBACK HEALTH CHECK FAILED", file=sys.stderr)
                else:
                    current.unlink(missing_ok=True)
                raise
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    print(f"Deployed {revision}")


def main():
    # Fixed root-owned config; neither SSH nor the archive can override paths.
    config = json.loads(Path("/etc/banasdev/deploy.json").read_text())
    if sys.argv[1:] == ["status"]:
        print((Path(config["state_dir"]) / "current/public/revision.txt").read_text().strip())
    elif len(sys.argv) == 3:
        deploy(config, sys.argv[1], sys.argv[2], sys.stdin.buffer)
    else:
        raise SystemExit("Expected status or REVISION ARCHIVE_SHA256")


if __name__ == "__main__":
    main()
