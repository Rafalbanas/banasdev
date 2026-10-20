import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

from deploy.deploy import deploy
from scripts.package import package

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        data = self.root / "data"
        data.mkdir()
        for name in ("data.json", "history.json", "weather.json"):
            (data / name).write_text('{"live":true}')
        (data / "weather_history.db").write_bytes(b"existing database")
        state = self.root / "state"
        self.config = {"state_dir": str(state), "data_dir": str(data),
                       "health_attempts": 1, "health_interval": 0}
        handler = lambda *args, **kwargs: QuietHandler(
            *args, directory=str(state / "current/public"), **kwargs)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.config["health_url"] = f"http://127.0.0.1:{self.server.server_port}"

    def payload(self, revision):
        output = io.BytesIO()
        package(ROOT, output, revision)
        return output.getvalue()

    def send(self, revision, payload):
        deploy(self.config, revision, hashlib.sha256(payload).hexdigest(), io.BytesIO(payload))

    def test_release_redeploy_and_persistent_weather(self):
        revision = "a" * 40
        payload = self.payload(revision)
        self.send(revision, payload)
        self.send(revision, payload)
        public = Path(self.config["state_dir"]) / "current/public"
        self.assertEqual((public / "index.html").read_bytes(), (ROOT / "index.html").read_bytes())
        self.assertEqual((public / "weather.json").read_text(), '{"live":true}')
        data = Path(self.config["data_dir"])
        (data / "weather.json").write_text('{"updated":true}')
        self.assertEqual((public / "weather.json").read_text(), '{"updated":true}')
        self.assertEqual((data / "weather_history.db").read_bytes(), b"existing database")
        self.assertFalse((public / "fetch_weather.py").exists())

    def test_redeploy_preserves_original_rollback_target(self):
        self.send("a" * 40, self.payload("a" * 40))
        self.send("b" * 40, self.payload("b" * 40))
        previous = Path(self.config["state_dir"]) / "previous"
        saved = previous.read_text()
        self.send("b" * 40, self.payload("b" * 40))
        self.assertEqual(previous.read_text(), saved)
        self.assertIn("a" * 40, saved)

    def test_failed_health_restores_previous_release(self):
        self.send("a" * 40, self.payload("a" * 40))
        from deploy.deploy import healthy
        with patch("deploy.deploy.healthy", side_effect=lambda config, sha, digest:
                   False if sha == "b" * 40 else healthy(config, sha, digest)):
            with self.assertRaisesRegex(RuntimeError, "health"):
                self.send("b" * 40, self.payload("b" * 40))
        current = Path(self.config["state_dir"]) / "current/public/revision.txt"
        self.assertEqual(current.read_text().strip(), "a" * 40)

    def test_rejects_traversal_before_switch(self):
        output = io.BytesIO(self.payload("a" * 40))
        with zipfile.ZipFile(output, "a") as archive:
            archive.writestr("../../escape", "bad")
        with self.assertRaisesRegex(ValueError, "entries"):
            self.send("a" * 40, output.getvalue())
        self.assertFalse((self.root / "escape").exists())
        self.assertFalse((Path(self.config["state_dir"]) / "current").exists())

    def test_rejects_corrupt_digest_and_wrong_revision(self):
        payload = self.payload("a" * 40)
        with self.assertRaisesRegex(ValueError, "digest"):
            deploy(self.config, "a" * 40, "0" * 64, io.BytesIO(payload))
        with self.assertRaisesRegex(ValueError, "revision mismatch"):
            self.send("b" * 40, payload)

    def test_live_json_cannot_be_overwritten_by_archive(self):
        output = io.BytesIO(self.payload("a" * 40))
        with zipfile.ZipFile(output, "a") as archive:
            archive.writestr("public/weather.json", "{}")
        with self.assertRaisesRegex(ValueError, "entries"):
            self.send("a" * 40, output.getvalue())


class CollectorTests(unittest.TestCase):
    def test_configured_data_directory_and_atomic_export(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {"BANASDEV_DATA_DIR": directory}):
                spec = importlib.util.spec_from_file_location("isolated_collector", ROOT / "fetch_weather.py")
                collector = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(collector)
            for path in (collector.OUTPUT_PATH, collector.DATABASE_PATH,
                         collector.HISTORY_PATH, collector.WEATHER_PATH):
                self.assertEqual(path.parent, Path(directory))
            collector.write_json_atomically({"temperature": 12.5}, collector.WEATHER_PATH)
            self.assertEqual(json.loads(collector.WEATHER_PATH.read_text()), {"temperature": 12.5})
            self.assertEqual(list(Path(directory).iterdir()), [collector.WEATHER_PATH])


if __name__ == "__main__":
    unittest.main()
