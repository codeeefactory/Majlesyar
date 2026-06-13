# Majlesyar GeoDNS, Monitoring, and Failover

This directory adds a repo-managed path for Phase 9 through Phase 12:

- GeoDNS with PowerDNS Authoritative and the GeoIP backend
- MaxMind GeoLite2 Country updates
- Iran and global probe execution
- conservative automatic failover plus manual overrides
- origin and maintenance Nginx templates
- Prometheus scrape and alert rules
- role-aware bootstrap through the root `startup.sh`

## Startup Roles

The root `startup.sh` now supports these values for `DEPLOY_ROLE`:

- `origin`: deploys the app container, Nginx, backups, host metrics, and security basics
- `maintenance`: deploys the static maintenance page host plus host metrics and hardening
- `dns`: deploys PowerDNS Authoritative, MaxMind updates, host metrics, and, on the primary DNS node, the failover timer and optional Prometheus
- `probe`: deploys the probe timer and node exporter

Examples:

```bash
DEPLOY_ROLE=origin \
DOMAIN=majlesyar.com \
ORIGIN_SERVER_NAMES="majlesyar.com ir-origin.majlesyar.com" \
CERTBOT_EMAIL=ops@example.com \
CERTBOT_DOMAINS="majlesyar.com ir-origin.majlesyar.com" \
MONITORING_SOURCE_CIDR=203.0.113.10/32 \
./startup.sh
```

```bash
DEPLOY_ROLE=dns \
DNS_PRIMARY=1 \
PROMETHEUS_ENABLE=1 \
MAXMIND_ACCOUNT_ID=123456 \
MAXMIND_LICENSE_KEY=replace-me \
SECONDARY_SSH_TARGET=root@ns2.majlesyar.com \
MONITORING_SOURCE_CIDR=203.0.113.10/32 \
./startup.sh
```

```bash
DEPLOY_ROLE=probe \
REGION=iran \
CONTROLLER_SSH_TARGET=root@ns1.majlesyar.com \
MONITORING_SOURCE_CIDR=203.0.113.10/32 \
./startup.sh
```

## Files That Matter

- `config/site.yaml`: source of truth for domain, origins, policy labels, and discovered current records
- `scripts/render_geo_zone.py`: renders `/etc/powerdns/geoip/majlesyar.com.yaml`
- `scripts/evaluate_failover.py`: converts fresh probe state into an effective routing policy
- `scripts/probe_runner.py`: checks DNS, direct origin HTTP/HTTPS health, TLS, and SOA serial
- `scripts/geodns_cycle.sh`: runs failover evaluation, renders the zone, reloads PowerDNS, and syncs to the secondary
- `scripts/manual_failover.sh`: pins Iran and default answers manually
- `scripts/manual_rollback.sh`: removes the override and returns control to automatic evaluation
- `scripts/export_cloudflare_zone.py`: exports the current Cloudflare zone before cutover

## What To Customize First

Before using the DNS role in production, replace the placeholder IP addresses in `config/site.yaml`:

- `ns1.majlesyar.com`
- `ns2.majlesyar.com`
- `ir-origin.majlesyar.com`
- `global-origin.majlesyar.com`
- `maintenance-origin.majlesyar.com`

The file currently preserves the public facts we observed on 2026-05-03:

- Cloudflare NS: `ariadne.ns.cloudflare.com`, `huxley.ns.cloudflare.com`
- SOA serial: `2400467473`
- apex A: `104.21.61.192`, `172.67.213.17`
- apex AAAA: `2606:4700:3037::ac43:d511`, `2606:4700:3033::6815:3dc0`
- TXT: `google-site-verification=...`
- `www` absent
- MX not observed in public queries
- DS not observed in public queries

Export the full Cloudflare zone before cutover because public DNS does not reveal every subdomain:

```bash
CLOUDFLARE_API_TOKEN=replace-me \
python3 /usr/local/lib/majlesyar/export_cloudflare_zone.py \
  --zone-name majlesyar.com \
  --output /root/majlesyar-cloudflare-zone.json
```

## Automatic Failover Logic

The automatic logic is intentionally conservative:

- if both origins are healthy: Iran gets `iran`, the rest gets `global`
- if Iran is unhealthy and global is healthy: Iran gets `global` only if the Iran probe can reach it, otherwise `maintenance`
- if global is unhealthy and Iran is healthy: the rest of the world gets `iran` only if the global probe can reach it, otherwise `maintenance`
- if both are unhealthy: everyone gets `maintenance`

Probe freshness defaults to 180 seconds.
State changes are delayed by a small hysteresis window to reduce flapping:

- 3 consecutive failures to mark a path down
- 2 consecutive successes to mark a path recovered

## Manual Failover

Pin traffic manually:

```bash
/usr/local/lib/majlesyar/manual_failover.sh \
  --ir maintenance \
  --default global \
  --reason "Iran origin maintenance window"
systemctl start majlesyar-geodns.service
```

Remove the override:

```bash
/usr/local/lib/majlesyar/manual_rollback.sh
systemctl start majlesyar-geodns.service
```

The override file path matches the `startup.sh` DNS role default:

```bash
/opt/majlesyar_geodns/state/manual-override.json
```

## Monitoring Coverage

The repo now covers these checks:

1. Authoritative DNS availability from Iran and global probes
2. DNS response correctness from Iran and global probes
3. Iran and global direct origin HTTP/HTTPS health
4. TLS validity for the public hostname and direct origin hostnames
5. SOA serial consistency across authoritative servers
6. MaxMind DB freshness on DNS nodes
7. PowerDNS service health on DNS nodes
8. Nginx and app health on origin and maintenance nodes

Prometheus rules live in `monitoring/alerts.yml`.

## Security Notes

`startup.sh` applies these defaults by role:

- UFW deny-by-default with only role-appropriate ports opened
- TCP and UDP 53 only on `dns`
- no recursor installation anywhere
- PowerDNS API and webserver bound to localhost only
- MaxMind key stored in `/etc/GeoIP.conf` with mode `0600`
- fail2ban enabled
- optional SSH password-auth disable through `SSH_DISABLE_PASSWORD_AUTH=1`

## Cutover Sequence

1. Run `startup.sh` for the maintenance host.
2. Run `startup.sh` for the Iran and global origins.
3. Run `startup.sh` for the DNS primary and secondary.
4. Run `startup.sh` for the Iran and global probes.
5. Replace placeholder addresses in `config/site.yaml` on the DNS primary and rerun `systemctl start majlesyar-geodns.service`.
6. Export the Cloudflare zone and merge any missing records into `config/site.yaml`.
7. Lower TTLs before registrar changes.
8. Create registrar glue for `ns1.majlesyar.com` and `ns2.majlesyar.com`.
9. Update registrar nameservers away from Cloudflare only after direct origin and DNS tests pass.

## Rollback

Rollback is easiest if you keep the Cloudflare zone export and the previous registrar nameserver settings:

- change registrar nameservers back to Cloudflare
- keep the existing DNS primary rendered zone as a fallback record of the cutover state
- on the origin side, use the existing `rollback.sh` for app data and code rollback
