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
