// Custom Caddy entrypoint. Keep module versions in go.mod and go.sum.
package main

import (
	_ "github.com/WeidiDeng/caddy-cloudflare-ip"
	_ "github.com/caddy-dns/cloudflare"
	_ "github.com/caddyserver/cache-handler"
	caddycmd "github.com/caddyserver/caddy/v2/cmd"
	_ "github.com/caddyserver/caddy/v2/modules/standard"
	_ "github.com/darkweak/storages/otter/caddy"
	_ "github.com/fvbommel/caddy-combine-ip-ranges"
	_ "github.com/fvbommel/caddy-dns-ip-range"
	_ "github.com/hslatman/caddy-crowdsec-bouncer/http"
	_ "github.com/lucaslorentz/caddy-docker-proxy/v2"
	_ "github.com/mholt/caddy-l4"
	_ "github.com/mholt/caddy-webdav"
)

func main() { caddycmd.Main() }
