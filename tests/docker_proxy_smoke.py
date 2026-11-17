"""Verify label discovery and upstream routing using an isolated label namespace."""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import uuid


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def main():
    image = sys.argv[1]
    token = 'caddytest' + uuid.uuid4().hex[:10]
    network, backend, proxy = token + 'net', token + 'backend', token + 'proxy'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    subnet = os.environ.get('CADDY_TEST_NETWORK_SUBNET')
    network_args = ['--subnet', subnet] if subnet else []
    docker('network', 'create', *network_args, network)
    try:
        docker('run', '-d', '--name', backend, '--network', network,
               '--label', f'{token}=http://probe.test',
               '--label', f'{token}.reverse_proxy={{{{upstreams 8080}}}}',
               image, 'caddy', 'respond', '--listen', ':8080', '--body', 'docker-proxy-ok')
        docker('run', '-d', '--name', proxy, '--network', network,
               '-p', f'127.0.0.1:{port}:80',
               '-v', '/var/run/docker.sock:/var/run/docker.sock:ro',
               '-e', f'CADDY_DOCKER_LABEL_PREFIX={token}',
               '-e', f'CADDY_INGRESS_NETWORKS={network}',
               image, 'caddy', 'docker-proxy')
        for _ in range(100):
            try:
                req = urllib.request.Request(f'http://127.0.0.1:{port}', headers={'Host': 'probe.test'})
                with urllib.request.urlopen(req, timeout=2) as response:
                    assert response.read() == b'docker-proxy-ok'
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise AssertionError('Docker label route did not become ready')
        # No unrelated hostname should have been imported from the shared daemon.
        config = json.loads(docker('exec', proxy, 'wget', '-qO-', 'http://127.0.0.1:2019/config/'))
        hosts = []
        def visit(obj):
            if isinstance(obj, dict):
                if 'host' in obj and isinstance(obj['host'], list):
                    hosts.extend(obj['host'])
                for value in obj.values():
                    visit(value)
            elif isinstance(obj, list):
                for value in obj:
                    visit(value)
        visit(config)
        assert hosts == ['probe.test'], hosts
        print('PASS: isolated Docker label discovery, backend routing, and admin config API')
    except BaseException:
        subprocess.run(['docker', 'logs', '--tail', '40', proxy], check=False)
        raise
    finally:
        subprocess.run(['docker', 'rm', '-f', proxy, backend], check=False, stdout=subprocess.DEVNULL)
        subprocess.run(['docker', 'network', 'rm', network], check=False, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
