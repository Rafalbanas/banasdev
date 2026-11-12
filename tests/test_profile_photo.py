"""Only the high-resolution static portrait belongs in a release."""
import io
from pathlib import Path
import unittest
import zipfile

from deploy.deploy import FILES
from scripts.package import package

ROOT = Path(__file__).resolve().parents[1]


class ProfilePhotoTests(unittest.TestCase):
    def test_static_portrait(self):
        html = (ROOT / "index.html").read_text()
        self.assertIn('src="cv_photo.webp?v=20261111"', html)
        self.assertIn('width="1125" height="842"', html)
        for removed in ("cv_photo2", "photoSwitch", "photoIndex", "photoHint", "changePhoto"):
            self.assertNotIn(removed, html)

    def test_release_has_no_second_portrait(self):
        output = io.BytesIO()
        package(ROOT, output, "a" * 40)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()), FILES)
            self.assertIn("public/cv_photo.webp", archive.namelist())
            self.assertFalse(any("cv_photo2" in name for name in archive.namelist()))
        for extension in ("jpg", "webp"):
            self.assertFalse((ROOT / f"cv_photo2.{extension}").exists())
