# Dependency review — 2026-11-17

Candidates must be stable and at least seven days old. Release publication dates
are used where available; Go proxy source timestamps are used for module tags
without a GitHub Release. Builder and runtime manifests are digest-pinned; the
selected platform images were created on November 5. The rejected Caddy builder
image was rebuilt on November 10 and did not meet the seven-day window.

| Component | Previously pinned | Selected | Published/source date | Reason |
|---|---|---|---|---|
| Caddy | 2.11.4 | 2.11.9 | November 5 | Proxy/streaming corrections, FastCGI security fixes, TLS client-auth conflict validation, path-placeholder fixes |
| CrowdSec bouncer | 0.14.1 (live Rogue: 0.13.1) | 0.15.0 | November 2 | Block-reason variables, decision precedence, LAPI timeouts; retains cancellable streaming shutdown |
| Docker Proxy | obsolete `plugin/v2` 2.9.9 | current `/v2` 2.13.1 | July 2 | Current Docker/Moby support, in-process config loads, explicit logging controls, restored admin API default |
| HTTP cache handler | 0.16.0 | 0.17.0 | September 17 | Souin 1.7.9 dependency update |
| Otter cache storage | 0.0.19 | 0.0.23 | November 9 | Compatible current storage/core dependency set; retain explicit Otter registration |
| Layer 4 | 0.1.2 | 0.1.2 | July 16 | 0.1.3 was published November 12: too young |
| Cloudflare DNS | 0.2.4 | 0.2.4 | March 23 | Already current |
| WebDAV | fa2f366b0d75 | unchanged | January 27 | Already current |
| Cloudflare IP ranges | f53b62aa13cb | unchanged | November 30, 2023 | Already current |
| DNS IP ranges | 0.0.2 | unchanged | February 28, 2023 | Already current |
| Combined IP ranges | 0.0.1 | unchanged | March 1, 2023 | Already current |
| Go toolchain | implicit builder version | 1.27.3 | image: November 5 | Meets minimum Go version; blocks automatic toolchain upgrades |

The small committed `main.go` replaces xcaddy's temporary generated entrypoint.
`go.mod` and `go.sum` lock the complete selected dependency graph. Builds use
`-mod=readonly`, `GOTOOLCHAIN=local`, and the existing build tags. The Docker
Proxy module changed import paths upstream: `plugin/v2@v2.13.1` does not exist.

## Features and compatibility

These updates do not enable a WAF, CAPTCHA, new caching policy, or new listeners.
Existing Caddyfiles must adapt and validate before a rollout. Caddy 2.11.9 rejects
conflicting TLS client authentication for the same host and ambiguous FastCGI
script paths. Bouncer 0.15.0 exposes `{http.vars.crowdsec.module}`, `.origin`,
`.remediation`, and `.duration` for future precise block logging; it also supports
an explicit `lapi_timeout`. HTTPS LAPI clients now honor proxy environment
variables, so inspect `NO_PROXY` before using HTTPS with a global proxy.

## Local validation

```sh
docker build -t caddy-deps:20261117 .
python3 tests/nonroot_bind_smoke.py caddy-deps:20261117
python3 tests/dependency_age.py caddy-deps:20261117
python3 tests/reload_smoke.py caddy-deps:20261117
python3 tests/docker_proxy_smoke.py caddy-deps:20261117
docker buildx build --platform linux/arm64 --load -t caddy-deps:20261117-arm64 .
```

On hosts with exhausted Docker address pools, set `CADDY_TEST_NETWORK_SUBNET`
to an inspected, unused subnet for the Docker Proxy smoke test.

The age gate checks every module embedded in the resulting binary against Go
proxy metadata, plus the recorded release and base-image dates. It fails closed
on unknown metadata. Release dates are retained in `dependency-releases.json`.

## Publication and rollout

The existing workflow runs on pushes to main or published releases, not PRs or
feature-branch pushes. It builds and tests amd64 before publishing amd64/arm64.
The added age gate runs before publication. Do not trigger a separate release
workflow for the same change; a single approved merge/push to main is sufficient.

Before replacing a live ingress, retain its exact image, Compose configuration,
Caddyfile/imports, effective configuration, and certificate storage. Validate
using the candidate and isolated copies of writable storage. Replace one node at
a time, keeping the old image/config for rollback. Verify config API, repeated
reloads, TLS, HTTP/2/3, WebSockets/h2c where used, CrowdSec polling and bans.

## Sources

- https://github.com/caddyserver/caddy/releases/tag/v2.11.9
- https://github.com/caddyserver/caddy/releases/tag/v2.11.8
- https://github.com/hslatman/caddy-crowdsec-bouncer/releases/tag/v0.15.0
- https://github.com/hslatman/caddy-crowdsec-bouncer/releases/tag/v0.14.0
- https://github.com/lucaslorentz/caddy-docker-proxy/releases/tag/v2.13.1
- https://github.com/lucaslorentz/caddy-docker-proxy/releases/tag/v2.13.0
- https://github.com/caddyserver/cache-handler/compare/v0.16.0...v0.17.0
- https://github.com/mholt/caddy-l4/releases/tag/v0.1.3
- https://proxy.golang.org/github.com/darkweak/storages/otter/caddy/@v/v0.0.23.info

## Non-root privileged ports

The binary retains `cap_net_bind_service=ep`, matching the official Caddy image.
A native capability stage applies this attribute before the final COPY, allowing
amd64/arm64 cross-compilation without executing an arm64 tool. The non-root smoke
test runs UID 1000 with `ip_unprivileged_port_start=1024` and verifies port 443.
Without this attribute, host-network services on a normal privileged-port kernel
fail at startup even though configuration validation and high-port tests pass.
