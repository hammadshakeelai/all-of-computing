"""Run: python server.py --open. Python 3.11+, no external packages required."""
import argparse
import hmac
import json
import mimetypes
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from learning.app import LearningApp
from learning.providers import ProviderError

ROOT = Path(__file__).resolve().parent
MAX_BODY = 12 * 1024 * 1024


def make_server(app, port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Never log query strings, request bodies, keys, or learner content.
            pass

        def authorized_host(self):
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            origin = self.headers.get("Origin")
            return host in allowed and (not origin or origin in {"http://" + h for h in allowed})

        def respond(self, status, payload, content_type="application/json; charset=utf-8", attachment=None):
            body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if attachment:
                self.send_header("Content-Disposition", 'attachment; filename="' + attachment + '"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.authorized_host():
                return self.respond(403, {"error": "Only this local app origin is allowed."})
            parsed = urlparse(self.path)
            try:
                with app.store.lock:
                    if parsed.path == "/api/state":
                        return self.respond(200, app.state() | {"csrf_token": token})
                    if parsed.path == "/api/search":
                        query = parse_qs(parsed.query).get("q", [""])[0][:500]
                        return self.respond(200, {"results": app.store.search(query)})
                    if parsed.path == "/api/export":
                        if not hmac.compare_digest(self.headers.get("X-App-Token", ""), token):
                            return self.respond(403, {"error": "Refresh the app before exporting."})
                        return self.respond(200, app.export(), attachment="learning-backup.json")
                files = {"/": "index.html", "/app.js": "app.js", "/styles.css": "styles.css", "/favicon.svg": "favicon.svg"}
                if parsed.path not in files:
                    return self.respond(404, {"error": "Not found"})
                p = ROOT / "web" / files[parsed.path]
                return self.respond(200, p.read_bytes(), mimetypes.guess_type(str(p))[0] or "application/octet-stream")
            except (ValueError, OSError):
                self.respond(500, {"error": "Could not read local data. Check your data directory and restart."})

        def do_POST(self):
            if not self.authorized_host() or not hmac.compare_digest(self.headers.get("X-App-Token", ""), token):
                return self.respond(403, {"error": "Refresh this local app before saving."})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.respond(415, {"error": "Expected JSON."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY:
                    return self.respond(413, {"error": "Request is empty or exceeds 12 MB."})
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Expected an object.")
                path = urlparse(self.path).path
                if not path.startswith("/api/"):
                    return self.respond(404, {"error": "Not found"})
                result = app.dispatch(path[5:], data)
                self.respond(200, result)
            except ProviderError as error:
                self.respond(502, {"error": str(error), "work_saved": True})
            except (ValueError, KeyError, TypeError, RecursionError) as error:
                with app.store.lock:
                    app.store.db.rollback()
                self.respond(400, {"error": str(error) if isinstance(error, ValueError) else "Invalid request or archive."})
            except Exception:
                with app.store.lock:
                    app.store.db.rollback()
                self.respond(500, {"error": "Could not complete the operation. Your previous saved records are intact. Check storage and retry."})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="Local AI learning companion")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "private")
    parser.add_argument("--open", action="store_true", help="Open the app in your default browser")
    args = parser.parse_args()
    app = LearningApp(args.data_dir)
    server = make_server(app, args.port)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Learning companion: {url}\nData directory: {app.store.root}\nPress Ctrl+C to stop.", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.store.close()


if __name__ == "__main__":
    main()
