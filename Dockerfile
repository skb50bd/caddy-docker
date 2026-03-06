FROM caddy:builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/mholt/caddy-webdav \
    --with github.com/mholt/caddy-l4 \
    --with github.com/WeidiDeng/caddy-cloudflare-ip \
    --with github.com/caddyserver/cache-handler \
    --with github.com/darkweak/storages/otter/caddy

FROM caddy:latest

COPY --from=builder /usr/bin/caddy /usr/bin/caddy

EXPOSE 2019
HEALTHCHECK --interval=10s --timeout=10s --start-period=5s --retries=10 \
    CMD wget --no-verbose -T 1 http://127.0.0.1:2019/metrics -O - || exit 1
