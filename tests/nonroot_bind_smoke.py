"""Reproduce non-root host networking's privileged-port requirement in isolation."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid


def main():
    image = sys.argv[1]
    name = 'caddy-bind-test-' + uuid.uuid4().hex[:10]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    config = {'admin': {'disabled': True}, 'apps': {'http': {'servers': {'test': {
        'listen': [':443'], 'automatic_https': {'disable': True},
        'routes': [{'handle': [{'handler': 'static_response', 'body': 'nonroot-bind-ok'}]}],
    }}}}}
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text(json.dumps(config))
            path.chmod(0o644)
            subprocess.run([
                'docker', 'run', '-d', '--name', name, '--user', '1000:1000',
                '--cap-drop', 'ALL', '--cap-add', 'NET_BIND_SERVICE',
                '--sysctl', 'net.ipv4.ip_unprivileged_port_start=1024',
                '--mount', f'type=bind,source={path},target=/test/config.json,readonly',
                '--tmpfs', '/data:mode=1777', '--tmpfs', '/config:mode=1777',
                '-p', f'127.0.0.1:{port}:443', image, 'caddy', 'run',
                '--config', '/test/config.json',
            ], check=True, stdout=subprocess.DEVNULL)
            for _ in range(50):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}', timeout=2) as response:
                        assert response.read() == b'nonroot-bind-ok'
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise AssertionError('UID 1000 could not serve a privileged port')
            uid = subprocess.check_output(['docker', 'exec', name, 'id', '-u'], text=True).strip()
            assert uid == '1000', uid
            print('PASS: UID 1000 binds port 443 with privileged-port threshold 1024')
    except BaseException:
        subprocess.run(['docker', 'logs', '--tail', '30', name], check=False)
        raise
    finally:
        subprocess.run(['docker', 'rm', '-f', name], check=False, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
