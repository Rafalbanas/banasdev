"""Package only deployable source; live JSON and SQLite never enter a release."""
import argparse
from pathlib import Path
import re
import zipfile

PUBLIC_FILES = (
    "index.html", "robots.txt", "favicon.png", "cv_photo.jpg", "cv_photo.webp",
    "cv_photo2.jpg", "cv_photo2.webp",
)


def package(root, output, revision):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Expected a full Git commit SHA")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in PUBLIC_FILES:
            archive.write(root / name, "public/" + name)
        archive.writestr("public/revision.txt", revision + "\n")
        archive.write(root / "fetch_weather.py", "fetch_weather.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    package(Path(__file__).resolve().parents[1], args.output, args.revision)
