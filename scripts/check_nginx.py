"""Validate repository Nginx rules in an isolated local instance, never reload live Nginx."""
import http.client
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def check():
    temporary_root = "/tmp/opencode" if Path("/tmp/opencode").is_dir() else None
    with tempfile.TemporaryDirectory(prefix="banasdev-nginx-", dir=temporary_root) as directory:
        base = Path(directory)
        base.chmod(0o755)
        public = base / "public"
        public.mkdir(mode=0o755)
        (public / "index.html").write_text("<!doctype html><title>Local header check</title>")
        (public / "favicon.png").write_bytes(b"header-test")
        for name in ("index", "projekty", "hobby"):
            (public / f"{name}.md").write_text(f"# Markdown {name}\n")
            if name != "index":
                (public / f"{name}.html").write_text(f"<!doctype html><title>{name}</title>")
        (public / ".well-known").mkdir()
        for name in ("sitemap.xml", "robots.txt", "openapi.json", "api.md", ".well-known/api-catalog"):
            (public / name).write_bytes((ROOT / name).read_bytes())
        certificate, key = base / "cert.pem", base / "key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-subj", "/CN=localhost", "-keyout", str(key), "-out", str(certificate)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        http_port, https_port = free_port(), free_port()
        while http_port == https_port:
            https_port = free_port()
        source = (ROOT / "deploy/nginx-public.conf").read_text()
        source = source.replace("listen 80;", f"listen 127.0.0.1:{http_port};")
        source = source.replace("listen [::]:80;", "")
        source = source.replace("listen 443 ssl http2;", f"listen 127.0.0.1:{https_port} ssl http2;")
        source = source.replace("listen [::]:443 ssl http2;", "")
        source = source.replace("/etc/nginx/ssl/cert.pem", str(certificate)).replace("/etc/nginx/ssl/key.key", str(key))
        source = source.replace("/var/lib/banasdev/current/public", str(public))
        config = base / "nginx.conf"
        config.write_text(f"pid {base / 'nginx.pid'};\nerror_log {base / 'error.log'};\n"
                          "events {}\nhttp { include /etc/nginx/mime.types; access_log off;\n" + source + "\n}\n")
        command = ["nginx", "-p", str(base), "-c", str(config)]
        subprocess.run(command + ["-t"], check=True)
        process = subprocess.Popen(command + ["-g", "daemon off;"])
        try:
            context = ssl.create_default_context(cafile=str(certificate))
            context.check_hostname = False  # Locally generated CA, connecting to loopback IP only.
            for _ in range(100):
                try:
                    with socket.create_connection(("127.0.0.1", https_port), timeout=0.1):
                        break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError((base / "error.log").read_text())
                    time.sleep(0.05)
            for path in ("/", "/index.html", "/favicon.png", "/not-found"):
                connection = http.client.HTTPSConnection("127.0.0.1", https_port, context=context, timeout=5)
                connection.request("GET", path, headers={"Host": "banas.dev"})
                response = connection.getresponse()
                assert response.status == (404 if path == "/not-found" else 200), (path, response.status)
                headers = dict((key.lower(), value) for key, value in response.getheaders())
                assert headers["strict-transport-security"] == "max-age=300", path
                assert "frame-ancestors 'none'" in headers["content-security-policy"], path
                assert headers["x-frame-options"] == "DENY", path
                assert headers["x-content-type-options"] == "nosniff", path
                assert headers["referrer-policy"] == "strict-origin-when-cross-origin", path
                if path in ("/", "/index.html"):
                    assert '<https://banas.dev/>; rel="canonical"' in headers["link"]
                    for relation in ("api-catalog", "service-desc", "service-doc", "describedby"):
                        assert f'rel="{relation}"' in headers["link"]
                response.read()
                connection.close()
            for path in ("/", "/index.html", "/projekty.html", "/hobby.html", "/hobby.html?lang=en"):
                for accept, markdown in (("text/markdown", True), ("text/html", False),
                                         ("text/markdown;q=0", False),
                                         ("text/markdown; q=0.0, text/html", False),
                                         ("text/markdown;q=0.8, text/html;q=0.5", True)):
                    connection = http.client.HTTPSConnection("127.0.0.1", https_port, context=context, timeout=5)
                    connection.request("GET", path, headers={"Host": "banas.dev", "Accept": accept})
                    response = connection.getresponse()
                    body = response.read().decode()
                    assert response.status == 200, (path, accept, response.status)
                    expected_type = "text/markdown" if markdown else "text/html"
                    assert response.getheader("Content-Type").startswith(expected_type), (path, accept, response.getheaders())
                    assert body.startswith("# Markdown" if markdown else "<!doctype html>"), (path, accept, body)
                    assert response.getheader("Vary") == "Accept"
                    assert response.getheader("Cache-Control") == "no-store"
                    connection.close()
            for path, content_type in (("/sitemap.xml", "text/xml"),
                                       ("/.well-known/api-catalog", "application/linkset+json"),
                                       ("/openapi.json", "application/vnd.oai.openapi+json"),
                                       ("/api.md", "text/markdown")):
                connection = http.client.HTTPSConnection("127.0.0.1", https_port, context=context, timeout=5)
                connection.request("GET", path, headers={"Host": "banas.dev"})
                response = connection.getresponse()
                assert response.status == 200, (path, response.status)
                assert response.getheader("Content-Type").startswith(content_type), (path, response.getheaders())
                response.read()
                connection.close()
            connection = http.client.HTTPConnection("127.0.0.1", http_port, timeout=5)
            connection.request("GET", "/?test=1", headers={"Host": "banas.dev"})
            response = connection.getresponse()
            assert response.status == 301
            assert response.getheader("Location") == "https://banas.dev/?test=1"
            response.read()
            connection.close()
            print("Nginx OK: headers, redirects, sitemap/API catalog, HTML/Markdown negotiation, q=0 and cache isolation")
        finally:
            process.terminate()  # Only the test Nginx instance started above.
            process.wait(timeout=10)


if __name__ == "__main__":
    check()
