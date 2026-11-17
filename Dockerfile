# Release dates and the seven-day eligibility review are recorded in DEPENDENCIES.md.
FROM --platform=$BUILDPLATFORM golang:1.27.3-alpine@sha256:fa3d596898d9f126af7c01d14ee7597bab3f39cccf392ef36b69fe77cd681f18 AS builder
ARG TARGETOS
ARG TARGETARCH
ENV GOTOOLCHAIN=local
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY main.go ./
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS="${TARGETOS}" GOARCH="${TARGETARCH}" \
    go build -mod=readonly -trimpath -tags=nobadger,nomysql,nopgx -o /usr/bin/caddy .

# Apply file capabilities with native tools; never execute the target-architecture
# binary while cross-compiling. COPY preserves the resulting security.capability.
FROM --platform=$BUILDPLATFORM caddy:2.11.9@sha256:4851e54a46b206517c574821bb5cc67f170d2156041e9fbc4c9193b45e84a75b AS capability
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
RUN setcap cap_net_bind_service=+ep /usr/bin/caddy

FROM caddy:2.11.9@sha256:4851e54a46b206517c574821bb5cc67f170d2156041e9fbc4c9193b45e84a75b
COPY --from=capability /usr/bin/caddy /usr/bin/caddy
EXPOSE 2019
# Config API responsiveness also detects the historical CrowdSec reload deadlock.
HEALTHCHECK --interval=10s --timeout=10s --start-period=5s --retries=10 \
    CMD wget --no-verbose -T 3 http://127.0.0.1:2019/config/ -O /dev/null || exit 1
CMD ["caddy", "docker-proxy"]
