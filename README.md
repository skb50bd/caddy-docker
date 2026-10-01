# Caddy

A custom build of [Caddy](https://caddyserver.com/) reverse proxy container.

## Features

- [x] Cloudflare DNS support
- [x] WebDAV support
- [x] L4 support
- [x] Cloudflare IP support
- [x] Built-in container health check support when running in docker

## Usage

1. In your `Caddyfile`, add the following to get container health check working in docker.

```caddyfile
{
    metrics
}
```

2. For WebDAV support, follow the instructions [here](https://github.com/mholt/caddy-webdav).

3. For L4 support, follow the instructions [here](https://github.com/mholt/caddy-l4).

4. For Cloudflare IP support, follow the instructions [here](https://github.com/WeidiDeng/caddy-cloudflare-ip).

## Safe configuration reloads

CrowdSec is pinned to v0.14.1, which includes the cancellable decision-stream
shutdown fix (upstream PR #122). Older bouncers could hold Caddy's configuration
lock forever during Docker discovery reloads, leaving old container IPs active.
All other module versions and Caddy are pinned to the previously deployed versions.

CI runs `python3 tests/reload_smoke.py caddy-reload-test:ci` against an isolated
local fake LAPI before publishing. It verifies 30 real configuration reloads,
streaming decisions, HTTP responses, and admin API responsiveness. The image
health check queries `/config/`, because `/metrics` can succeed during the deadlock.
