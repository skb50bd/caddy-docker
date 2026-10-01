"""Exercise real CrowdSec streaming shutdown on repeated Caddy config reloads.

Runs only an isolated Docker container with a fake loopback LAPI. No production
credentials, Docker socket, certificates, or ingress networks are used.
"""
import http.server
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Lapi(http.server.BaseHTTPRequestHandler):
    streams = 0
    hold_next = threading.Event()
    inflight = threading.Event()
    release = threading.Event()

    def do_GET(self):
        if self.path.startswith("/v1/decisions/stream"):
            type(self).streams += 1
            if self.hold_next.is_set():
                self.hold_next.clear()
                self.inflight.set()
                self.release.wait(timeout=2)
            body = {"deleted": [], "new": [{
                "id": 1, "origin": "test", "scenario": "reload-regression",
                "scope": "Ip", "type": "ban", "value": "203.0.113.66",
                "duration": "1h",
            }]}
        elif self.path.startswith("/v1/decisions"):
            body = []
        else:
            body = {}
        encoded = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError):
            # A corrected bouncer cancels an in-flight LAPI request on shutdown.
            pass

    def log_message(self, *_args):
        pass


def request(url, data=None):
    headers = {"Content-Type": "application/json"} if data is not None else {}
    with urllib.request.urlopen(urllib.request.Request(
        url, data=None if data is None else json.dumps(data).encode(), headers=headers
    ), timeout=5) as response:
        return response.read()


def main():
    image = sys.argv[1]
    name = "caddy-reload-test-" + uuid.uuid4().hex[:10]
    lapi = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Lapi)
    threading.Thread(target=lapi.serve_forever, daemon=True).start()
    admin_port, http_port = free_port(), free_port()
    admin = f"http://127.0.0.1:{admin_port}"
    config = {
        "admin": {"listen": f"127.0.0.1:{admin_port}"},
        "apps": {
            "crowdsec": {
                "api_url": f"http://127.0.0.1:{lapi.server_port}",
                "api_key": "isolated-test-key", "ticker_interval": "20ms",
                "enable_streaming": True,
            },
            "http": {"servers": {"test": {
                "listen": [f"127.0.0.1:{http_port}"],
                "routes": [{"handle": [
                    {"handler": "crowdsec"},
                    {"handler": "static_response", "body": "reload-0"},
                ]}],
            }}},
        },
    }
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config))
            subprocess.run([
                "docker", "run", "-d", "--name", name, "--network", "host",
                "--mount", f"type=bind,source={path},target=/test/config.json,readonly",
                image, "caddy", "run", "--config", "/test/config.json",
            ], check=True, stdout=subprocess.DEVNULL)
            for attempt in range(50):
                try:
                    request(admin + "/config/")
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Caddy admin API did not start")
            versions = subprocess.check_output([
                "docker", "exec", name, "caddy", "list-modules", "--versions",
            ], text=True)
            assert "crowdsec v0.14.1" in versions, versions
            for iteration in range(1, 31):
                # Hold an old app's response across cancellation. Without the
                # upstream fix, its subsequent decision send has no consumer
                # and blocks Core.Shutdown while Caddy holds the config lock.
                Lapi.inflight.clear()
                Lapi.release.clear()
                Lapi.hold_next.set()
                assert Lapi.inflight.wait(timeout=2), "No in-flight streaming request"
                threading.Timer(0.15, Lapi.release.set).start()
                config["apps"]["http"]["servers"]["test"]["routes"][0]["handle"][1]["body"] = f"reload-{iteration}"
                request(admin + "/load", config)
                request(admin + "/config/")
                body = request(f"http://127.0.0.1:{http_port}")
                assert body == f"reload-{iteration}".encode(), body
                time.sleep(0.03)
            assert Lapi.streams >= 30, f"Only {Lapi.streams} streaming requests observed"
            profile = request(admin + "/debug/pprof/goroutine?debug=2").decode()
            assert "(*Core).Shutdown" not in profile, "Blocked CrowdSec shutdown"
            print(f"PASS: 30 real reloads, {Lapi.streams} LAPI streams, responsive routing and config API")
    except BaseException:
        subprocess.run(["docker", "logs", "--tail", "80", name], check=False)
        raise
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=False, stdout=subprocess.DEVNULL)
        lapi.shutdown()


if __name__ == "__main__":
    main()
