FROM caddy:2.11.4-builder AS builder

# Pin modules so rebuilding an ingress fix cannot silently upgrade unrelated plugins.
RUN xcaddy build v2.11.4 \
    --with github.com/caddy-dns/cloudflare@v0.2.4 \
    --with github.com/mholt/caddy-webdav@v0.0.0-20260127042217-fa2f366b0d75 \
    --with github.com/mholt/caddy-l4@v0.1.2 \
    --with github.com/WeidiDeng/caddy-cloudflare-ip@v0.0.0-20231130002422-f53b62aa13cb \
    --with github.com/fvbommel/caddy-dns-ip-range@v0.0.2 \
    --with github.com/fvbommel/caddy-combine-ip-ranges@v0.0.1 \
    --with github.com/caddyserver/cache-handler@v0.16.0 \
    --with github.com/darkweak/storages/otter/caddy@v0.0.19 \
    --with github.com/hslatman/caddy-crowdsec-bouncer/http@v0.14.1 \
    --with github.com/lucaslorentz/caddy-docker-proxy/plugin/v2@v2.9.9

FROM caddy:2.11.4

COPY --from=builder /usr/bin/caddy /usr/bin/caddy

EXPOSE 2019
# /metrics remains responsive during a config-lock deadlock; /config/ does not.
HEALTHCHECK --interval=10s --timeout=10s --start-period=5s --retries=10 \
    CMD wget --no-verbose -T 3 http://127.0.0.1:2019/config/ -O /dev/null || exit 1

CMD ["caddy", "docker-proxy"]
