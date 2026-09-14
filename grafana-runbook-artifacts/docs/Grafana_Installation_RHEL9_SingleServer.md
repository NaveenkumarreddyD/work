PRODUCTION INSTALLATION RUNBOOK

Grafana Monitoring Platform

Production Deployment on Red Hat Enterprise Linux 9

Grafana OSS • PostgreSQL 16 • Prometheus LTS • Alertmanager • Node Exporter

Prepared for on-premises DevOps application monitoring

Version 1.0  |  23 July 2026

# Document purpose and deployment decision

This runbook provides a complete production build, configuration, validation, backup, and recovery procedure for a Grafana monitoring platform on RHEL 9. It covers Grafana OSS, PostgreSQL, Prometheus, Alertmanager, and Node Exporter, co-located on one monitoring server that observes the organization's application and Linux servers.

> **Recovery model:** This design has no automatic failover. If the monitoring server fails, monitoring, dashboards, and alerting are unavailable until the server is restored or rebuilt from backup. Backup integrity and a rehearsed restore procedure are therefore the primary recovery controls and must meet the agreed recovery-time and recovery-point objectives.

> **External DNS and load balancing:** User-facing DNS, TLS termination, and any load balancer are provided separately by the organization's network and platform teams and are requested through the normal change process. This runbook exposes Grafana on HTTP port 3000 behind that organization-managed entry point; it does not install NGINX or a local reverse proxy.

| Item | Selected design |
| --- | --- |
| Operating system | Red Hat Enterprise Linux 9, x86_64 |
| Grafana | Grafana OSS, single instance on port 3000 |
| Grafana database | PostgreSQL 16, single local instance (loopback) |
| Metrics | Prometheus 3.13.1 LTS, single instance |
| Notifications | Alertmanager 0.33.1, single instance (no clustering) |
| Host metrics | Node Exporter 1.12.1 on this server and each application server |
| User access | HTTPS via organization-managed DNS and load balancer to Grafana :3000 |
| Recovery model | Restore from backup; no automatic failover |

## Scope

- Installation and service configuration of all components on one monitoring server.
- PostgreSQL 16 initialization and use as the Grafana backend database.
- Prometheus collection, retention controls, and alert rules.
- Alertmanager single-node notification routing and integration placeholders.
- Grafana installation, Prometheus data-source provisioning, and access hardening.
- Integration patterns for GitLab, Jenkins, SonarQube, Nexus, and Linux servers.
- Firewall, SELinux, authentication, backup, patching, monitoring, and acceptance tests.

## Out of scope

- Host or component high availability, replication, and automatic failover.
- User-facing DNS, TLS certificate issuance, and load-balancer configuration (organization supplied).
- A long-term deduplicating metrics store such as Thanos or Grafana Mimir.
- Organization-specific SSO, SMTP, Teams, ServiceNow, or PagerDuty credentials.
- Application changes that require approval from GitLab, Jenkins, SonarQube, or Nexus owners.

## Source-controlled artifacts

Store the following files in an approved private configuration repository. Never commit passwords, API tokens, private keys, or unencrypted database credentials.

- /etc/prometheus/prometheus.yml and /etc/prometheus/rules/*.yml
- /etc/alertmanager/alertmanager.yml with secrets supplied at deployment time
- /etc/grafana/grafana.ini and /etc/grafana/provisioning/
- Systemd unit files and the tested recovery procedure

# 1. Architecture and naming

## 1.1 Component placement

| Component | Host | Listen address | Notes |
| --- | --- | --- | --- |
| PostgreSQL 16 | Monitoring server | 127.0.0.1:5432 | Grafana backend database, loopback only |
| Grafana OSS | Monitoring server | 0.0.0.0:3000 | Reached by the organization load balancer |
| Prometheus LTS | Monitoring server | 127.0.0.1:9090 | Scrapes all targets, evaluates rules |
| Alertmanager | Monitoring server | 127.0.0.1:9093 | Single node, clustering disabled |
| Node Exporter | Monitoring + app servers | 0.0.0.0:9100 | Host metrics, restricted by firewall |

## 1.2 Replace these values

> **Before execution:** Replace every angle-bracket value in this runbook. Do not paste a command containing <PLACEHOLDER> into a production shell.

| Placeholder | Example | Purpose |
| --- | --- | --- |
| <MON_FQDN> | mon01.example.com | Monitoring server hostname |
| <MON_IP> | 10.10.10.11 | Monitoring server address |
| <GRAFANA_FQDN> | grafana.example.com | User-facing Grafana DNS (org LB) |
| <APPROVED_CIDR> | 10.20.0.0/16 | Authorized user / load-balancer network |
| <PROM_RETENTION_SIZE> | 40GB | ~80% of the 50 GB /u01 Prometheus mount |
| <SMTP_OR_WEBHOOK> | Organization supplied | Alert delivery destination |
| <BACKUP_PATH> | /backup/monitoring | Approved protected backup destination |

## 1.3 Data flow

```bash
Users --HTTPS/443--> Organization DNS + Load Balancer (TLS termination)
                          |
                          +--HTTP/3000--> Grafana (single host)
                                              |
                                              +--> Prometheus/9090 (loopback)
                                              +--> PostgreSQL/5432 (loopback)

Prometheus --> Node Exporter/9100 (local host and application servers)
Prometheus --> application metrics endpoints
Prometheus --> Alertmanager/9093 (loopback) --> Approved notification channel
```

## 1.4 Availability behavior

| Failure | Expected behavior | Required action |
| --- | --- | --- |
| A single component (Prometheus, Alertmanager, Grafana) | systemd restarts the failed unit automatically. | Investigate logs; confirm the service returned. |
| Node Exporter on an application server | That host's metrics gap; TargetDown alert fires. | Repair the exporter or host. |
| The monitoring server | All monitoring, dashboards, and alerting are unavailable. | Restore the host, then restore PostgreSQL and configuration from backup. |
| Corrupted or lost Grafana database | Dashboards, users, and data sources are lost. | Restore the latest PostgreSQL backup and restart Grafana. |

> **Recovery depends on backups:** Because recovery relies on rebuilding from backup rather than automatic failover, backup integrity and a rehearsed restore procedure are the primary recovery controls. Validate backups and test restores on a schedule (Section 11).

# 2. Prerequisites and security approvals

## 2.1 Server minimums

Final capacity must be calculated from target count, active time-series count, scrape interval, retention, dashboard concurrency, and alert volume. Because all components share one host, size generously. The following is a starting point, not an automatic sizing approval.

| Resource | Starting point | Notes |
| --- | --- | --- |
| CPU | 4-8 vCPU | Prometheus query and ingestion plus Grafana and PostgreSQL share the host. |
| Memory | 16 GB | Increase for high series cardinality or concurrent dashboards. |
| OS disk | 40 GB | Separate from Prometheus and PostgreSQL data where possible. |
| Prometheus data | 50 GB on /u01 (provisioned) | Dedicated local mount. Cap retention to ~40 GB; see 2.1.2. |
| PostgreSQL data | Default location, low volume | Grafana metadata only; kept on the OS/default filesystem. |
| Backup volume | Sized to retention policy | Separate/off-host protected location strongly preferred. |

## 2.1.1 Per-component resource share

On a single host the components share CPU and memory, so size the server to the sum, not to any one component. Prometheus dominates memory and disk; the others are comparatively light.

| Component | Memory (typical) | Disk | Notes |
| --- | --- | --- | --- |
| Prometheus | 4-8 GB | 50 GB /u01 | Scales ~linearly with active series (~7.5 KiB/series head, plus query and compaction overhead). |
| Grafana OSS | 2-4 GB | 10-20 GB SSD | Grafana's own 'small/medium' tier; grows with concurrent users and plugins. |
| PostgreSQL 16 | 0.5-1 GB | 20 GB SSD | Grafana metadata only (dashboards, users, settings); very low volume. |
| Alertmanager | ~100 MB | < 1 GB | Negligible. |
| Node Exporter | ~50 MB | None | Negligible. |
| OS + headroom | 2-3 GB | 40 GB | RHEL 9, logs, buffers, backup staging. |

## 2.1.2 Worked sizing example

Assume ~15 targets (GitLab, Jenkins, SonarQube, Nexus, plus their Node Exporters and a few Linux hosts), roughly 250,000 active series, a 30-second scrape interval, and 30-day retention.

- Ingestion: 250,000 series / 30 s = ~8,300 samples per second.
- Disk (Prometheus): retention_seconds x samples/s x bytes/sample. At ~8,300 samples/s and 1-2 bytes/sample this is roughly 1.0-1.4 GB/day. On the provisioned 50 GB /u01 mount, cap retention size at 40 GB (leaving ~20% headroom for WAL and compaction), which yields approximately 2-4 weeks of history at ~250,000 series - fewer days at higher cardinality.
- Memory: ~250,000 series x ~7.5 KiB is ~1.9 GB of head series, and Prometheus typically needs roughly twice that under load, so plan 4-6 GB for Prometheus alone. With Grafana, PostgreSQL, and the OS, 16 GB total leaves comfortable headroom.
> **Sizing basis:** Prometheus documents an average of 1-2 bytes stored per sample; memory scales with active series count. Recompute both figures from your real active-series count (Prometheus 'prometheus_tsdb_head_series' metric) after two weeks of production data, then adjust retention and RAM. Reducing series cardinality lowers storage more effectively than lengthening the scrape interval.

> **Grafana database requirement:** Grafana supports PostgreSQL 12 or later (this runbook uses 16); SQLite is not recommended for production. Do not place Prometheus data on NFS - the TSDB requires a local POSIX-compliant filesystem.

## 2.2 Required organizational inputs

- One registered and patched RHEL 9 server with sudo access.
- Forward and reverse DNS for the monitoring server.
- User-facing Grafana DNS name and load balancer targeting the server on port 3000.
- TLS termination at the load balancer (or a certificate if Grafana-native TLS is chosen).
- Approved notification service and credentials.
- Firewall approvals for the port matrix below.
- Approved backup location with access controls and retention policy.
- Application-owner approval to enable metrics endpoints or install plugins/exporters.

## 2.3 Port matrix

| Source | Destination | Port | Purpose |
| --- | --- | --- | --- |
| Organization load balancer | Grafana on monitoring server | 3000/TCP | Grafana HTTP (TLS terminated at LB) |
| Approved admin networks | Monitoring server SSH | 22/TCP | Administration |
| Prometheus (loopback) | Alertmanager (loopback) | 9093/TCP | Alert delivery, on-host |
| Prometheus | Node Exporter (this host + app servers) | 9100/TCP | Host metrics |
| Prometheus | PostgreSQL exporter if added | 9187/TCP | Optional DB metrics |
| Prometheus | Application endpoints | Application-specific | GitLab/Jenkins/SonarQube/Nexus metrics |

> **Security rule:** Do not expose Prometheus, Alertmanager, Node Exporter, or application metrics endpoints to public or general user networks. Bind them to loopback where possible and restrict remaining exporter ports to the monitoring server address and approved administrators.

# 3. Base RHEL 9 preparation

## 3.1 Confirm the host

```bash
cat /etc/redhat-release
uname -m
hostname -f
df -h
free -h
timedatectl
chronyc tracking
```

Confirm that `uname -m` returns `x86_64`. The binary URLs in this runbook are for AMD64/x86_64.

```bash
sudo dnf update -y
sudo dnf install -y curl wget tar gzip unzip vim policycoreutils-python-utils
sudo systemctl reboot
```

> **Change control:** Schedule and approve the RHEL patching and reboot. Reconnect after the server returns, then confirm the expected kernel and services.

## 3.2 Create data and backup mount points

This deployment uses a dedicated 50 GB filesystem mounted at `/u01` for Prometheus time-series data. Confirm it is present, a real mount (not a directory on the root filesystem), and local (not NFS). PostgreSQL keeps its small default location and backups are written off this host.

```bash
findmnt /u01
df -hT /u01
sudo install -d -o root -g root -m 0755 /u01/prometheus
sudo install -d -o root -g root -m 0750 /var/backups/monitoring
sudo install -d -o root -g root -m 0755 /etc/monitoring
```

> **Storage sizing note:** 50 GB is below the 100 GB+ that is comfortable for 30-day retention at moderate cardinality. On this mount, size Prometheus retention to roughly 40 GB and expect approximately 2-4 weeks of history depending on active-series count. Do not stage database or metric backups on /u01 - keep them off-host so a full or failed /u01 does not also lose the backups. See Section 2.1.2.

## 3.3 Confirm SELinux and firewall state

```bash
getenforce
sudo firewall-cmd --state
sudo firewall-cmd --get-active-zones
```

Keep SELinux enforcing. Do not disable SELinux to solve a configuration error. Add only the required SELinux policy or boolean after confirming the denied operation.

# 4. Install PostgreSQL 16

> **Database role:** PostgreSQL is the Grafana backend on the same host. Grafana connects over the loopback interface, so the database listens only on 127.0.0.1 and is never exposed to the network.

## 4.1 Install packages

```bash
sudo dnf module reset postgresql -y
sudo dnf module install postgresql:16/server -y
postgres --version
```

## 4.2 Initialize the database

```bash
sudo PGSETUP_INITDB_OPTIONS="--data-checksums" postgresql-setup --initdb
sudo -u postgres pg_controldata /var/lib/pgsql/data | grep "Data page checksum"
```

Expected result: `Data page checksum version` is non-zero.

## 4.3 Configure PostgreSQL

Edit `/var/lib/pgsql/data/postgresql.conf` and set:

```bash
listen_addresses = 'localhost'
port = 5432
password_encryption = 'scram-sha-256'
max_connections = 200
shared_buffers = '512MB'
log_connections = on
log_disconnections = on
log_line_prefix = '%m [%p] %u@%d %r '
```

Append the following to `/var/lib/pgsql/data/pg_hba.conf`. Loopback-only, SCRAM-authenticated access for the Grafana role:

```bash
host  grafana  grafana  127.0.0.1/32  scram-sha-256
host  grafana  grafana  ::1/128       scram-sha-256
```

> **Optional TLS:** Loopback database traffic does not traverse the network, so plaintext on 127.0.0.1 is acceptable for most policies. If local TLS is mandated, install server.crt/server.key/root.crt into /var/lib/pgsql/data, set ssl = on, and use ssl_mode = verify-full in grafana.ini (Section 8.4).

## 4.4 Start and create the Grafana role and database

```bash
sudo systemctl enable --now postgresql
sudo systemctl status postgresql --no-pager
sudo -u postgres psql -c "SELECT version();"
```

Open a PostgreSQL administrator session:

```bash
sudo -u postgres psql
```

At the `psql` prompt, run:

```bash
CREATE ROLE grafana LOGIN;
\password grafana

CREATE DATABASE grafana
  OWNER grafana
  ENCODING 'UTF8'
  TEMPLATE template0;

\q
```

> **Password handling:** Use a strong, unique password supplied by the approved secret-management process. Do not place passwords directly in shell commands, tickets, source control, or this document.

## 4.5 Verify connectivity

```bash
psql "host=127.0.0.1 port=5432 dbname=grafana user=grafana" -c "SELECT current_database();"
```

Expected: the command prompts for the Grafana password and returns `grafana`.

# 5. Install Node Exporter

Install Node Exporter on the monitoring server and later repeat the same procedure on every approved Linux application server.

## 5.1 Download and verify

```bash
cd /tmp
curl -fLO https://github.com/prometheus/node_exporter/releases/download/v1.12.1/node_exporter-1.12.1.linux-amd64.tar.gz

echo "b51d8a76aa2a9156a55d501aca6276fae09e262259a5e4e831d2c2222f084e63  node_exporter-1.12.1.linux-amd64.tar.gz" | sha256sum -c -

tar -xzf node_exporter-1.12.1.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin node_exporter
sudo install -m 0755 node_exporter-1.12.1.linux-amd64/node_exporter   /usr/local/bin/node_exporter
```

## 5.2 Create the service

```bash
sudo tee /etc/systemd/system/node_exporter.service >/dev/null <<'EOF'
[Unit]
Description=Prometheus Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=0.0.0.0:9100
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter
sudo systemctl status node_exporter --no-pager
curl -fsS http://localhost:9100/metrics | head
```

## 5.3 Firewall

On each Node Exporter host, allow TCP 9100 only from the monitoring server address.

```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4"   source address="<MON_IP>/32" port protocol="tcp" port="9100" accept'
sudo firewall-cmd --reload
```

On the monitoring server itself, Prometheus reaches Node Exporter over localhost, so no external rule is required for the local exporter.

# 6. Install Prometheus LTS

## 6.1 Download and verify

```bash
cd /tmp
curl -fLO https://github.com/prometheus/prometheus/releases/download/v3.13.1/prometheus-3.13.1.linux-amd64.tar.gz

echo "962b812371aff838d152b6ff2d56fdb7a6396f5542f48ebf73421b9721f0d103  prometheus-3.13.1.linux-amd64.tar.gz" | sha256sum -c -

tar -xzf prometheus-3.13.1.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin prometheus
sudo install -d -o prometheus -g prometheus -m 0750   /etc/prometheus /etc/prometheus/rules
sudo chown prometheus:prometheus /u01/prometheus
sudo chmod 0750 /u01/prometheus
sudo restorecon -Rv /u01/prometheus
sudo install -m 0755 prometheus-3.13.1.linux-amd64/prometheus   /usr/local/bin/prometheus
sudo install -m 0755 prometheus-3.13.1.linux-amd64/promtool   /usr/local/bin/promtool
```

The Prometheus TSDB lives on the dedicated `/u01` mount (`/u01/prometheus`). The `restorecon` step applies the default SELinux context to the data directory.

## 6.2 Prometheus configuration

Create `/etc/prometheus/prometheus.yml`. Targets on this host use localhost; application servers use their addresses.

```bash
global:
  scrape_interval: 30s
  scrape_timeout: 10s
  evaluation_interval: 30s
  external_labels:
    environment: production

rule_files:
  - /etc/prometheus/rules/*.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 127.0.0.1:9093

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets:
          - 127.0.0.1:9090

  - job_name: monitoring-server
    static_configs:
      - targets:
          - 127.0.0.1:9100

  - job_name: application-linux-servers
    static_configs:
      - targets:
          - <GITLAB_SERVER>:9100
          - <JENKINS_SERVER>:9100
          - <SONARQUBE_SERVER>:9100
          - <NEXUS_SERVER>:9100
```

## 6.3 Initial alert rules

Create `/etc/prometheus/rules/infrastructure.yml`:

```bash
groups:
  - name: infrastructure
    rules:
      - alert: TargetDown
        expr: up == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Monitoring target is unavailable"
          description: "{{ $labels.job }} target {{ $labels.instance }} is down."

      - alert: HostHighCPU
        expr: 100 - (avg by(instance)
          (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"

      - alert: HostLowMemory
        expr: (node_memory_MemAvailable_bytes /
          node_memory_MemTotal_bytes) * 100 < 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Available memory below 10% on {{ $labels.instance }}"

      - alert: HostFilesystemLow
        expr: 100 * node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} /
          node_filesystem_size_bytes{fstype!~"tmpfs|overlay"} < 15
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Filesystem space below 15% on {{ $labels.instance }}"
```

## 6.4 Validate ownership and syntax

```bash
sudo chown -R prometheus:prometheus /etc/prometheus /u01/prometheus
sudo promtool check config /etc/prometheus/prometheus.yml
sudo promtool check rules /etc/prometheus/rules/infrastructure.yml
```

## 6.5 Create the Prometheus service

> **Retention value:** Set <PROM_RETENTION_SIZE> to no more than approximately 80% of the /u01 filesystem so that WAL, compaction, and the head block have headroom. For the provisioned 50 GB mount, use 40GB. Both retention limits below apply together: whichever is reached first (30 days of time or 40 GB of size) triggers compaction of the oldest data.

```bash
sudo tee /etc/systemd/system/prometheus.service >/dev/null <<'EOF'
[Unit]
Description=Prometheus Monitoring Server
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus   --config.file=/etc/prometheus/prometheus.yml   --storage.tsdb.path=/u01/prometheus   --storage.tsdb.retention.time=30d   --storage.tsdb.retention.size=<PROM_RETENTION_SIZE>   --web.listen-address=127.0.0.1:9090
Restart=on-failure
RestartSec=5
LimitNOFILE=65536
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
ReadWritePaths=/u01/prometheus

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now prometheus
sudo systemctl status prometheus --no-pager
curl -fsS http://localhost:9090/-/healthy
curl -fsS http://localhost:9090/-/ready
```

## 6.6 Network access

Prometheus binds to 127.0.0.1 and is reached only by local Grafana. Do not expose the Prometheus UI on the network. For occasional admin access, use an SSH tunnel rather than opening port 9090.

# 7. Install Alertmanager

## 7.1 Download and verify

```bash
cd /tmp
curl -fLO https://github.com/prometheus/alertmanager/releases/download/v0.33.1/alertmanager-0.33.1.linux-amd64.tar.gz

echo "93d802cba6a8d27239d747ce117df7648d326ab67394e32247540b030e9842ba  alertmanager-0.33.1.linux-amd64.tar.gz" | sha256sum -c -

tar -xzf alertmanager-0.33.1.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin alertmanager
sudo install -d -o alertmanager -g alertmanager -m 0750   /etc/alertmanager /var/lib/alertmanager
sudo install -m 0755 alertmanager-0.33.1.linux-amd64/alertmanager   /usr/local/bin/alertmanager
sudo install -m 0755 alertmanager-0.33.1.linux-amd64/amtool   /usr/local/bin/amtool
```

## 7.2 Configure routing

Create `/etc/alertmanager/alertmanager.yml`. The initial null receiver is valid for build validation but must be replaced before go-live.

```bash
global:
  resolve_timeout: 5m

route:
  receiver: operations-placeholder
  group_by: [alertname, job]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: operations-placeholder
```

> **Go-live gate:** Production acceptance must fail until a test alert is successfully delivered to the approved notification channel and acknowledged by the support team.

## 7.3 Validate configuration

```bash
sudo chown -R alertmanager:alertmanager   /etc/alertmanager /var/lib/alertmanager
sudo amtool check-config /etc/alertmanager/alertmanager.yml
```

## 7.4 Create the service

Clustering is disabled on a single node by passing an empty cluster listen address.

```bash
sudo tee /etc/systemd/system/alertmanager.service >/dev/null <<'EOF'
[Unit]
Description=Prometheus Alertmanager
Wants=network-online.target
After=network-online.target

[Service]
User=alertmanager
Group=alertmanager
Type=simple
ExecStart=/usr/local/bin/alertmanager   --config.file=/etc/alertmanager/alertmanager.yml   --storage.path=/var/lib/alertmanager   --web.listen-address=127.0.0.1:9093   --cluster.listen-address=
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
ReadWritePaths=/var/lib/alertmanager

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now alertmanager
sudo systemctl status alertmanager --no-pager
curl -fsS http://localhost:9093/-/healthy
curl -fsS http://localhost:9093/-/ready
```

# 8. Install Grafana OSS

## 8.1 Add the official repository

```bash
cd /tmp
wget -q -O grafana-gpg.key https://rpm.grafana.com/gpg.key
sudo rpm --import grafana-gpg.key

sudo tee /etc/yum.repos.d/grafana.repo >/dev/null <<'EOF'
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF

sudo dnf makecache --refresh
sudo dnf install -y grafana
rpm -q grafana
```

## 8.2 Create Grafana secrets

Store the database password and Grafana `secret_key` through the organizational secret-management process. Grafana reads them from files, so they never appear in grafana.ini.

```bash
sudo install -d -o root -g grafana -m 0750 /etc/grafana/secrets
sudo vi /etc/grafana/secrets/postgres_password
sudo vi /etc/grafana/secrets/secret_key
sudo chown root:grafana /etc/grafana/secrets/*
sudo chmod 0640 /etc/grafana/secrets/*
```

Generate the secret key on an approved secure workstation and store it in the secret manager. It signs sessions and encrypts data-source secrets; keep it stable for the life of the database.

## 8.3 Configure Grafana

Edit `/etc/grafana/grafana.ini`. Grafana listens on port 3000 for the organization load balancer, which terminates TLS. `root_url` uses the external HTTPS name so links and redirects are correct.

```bash
[database]
type = postgres
host = 127.0.0.1:5432
name = grafana
user = grafana
password = $__file{/etc/grafana/secrets/postgres_password}
ssl_mode = disable
max_idle_conn = 10
max_open_conn = 100
conn_max_lifetime = 3600
migration_locking = true
locking_attempt_timeout_sec = 60

[server]
protocol = http
http_addr = 0.0.0.0
http_port = 3000
domain = <GRAFANA_FQDN>
root_url = https://<GRAFANA_FQDN>/
enforce_domain = false

[security]
secret_key = $__file{/etc/grafana/secrets/secret_key}
cookie_secure = true
cookie_samesite = strict

[users]
allow_sign_up = false

[auth.anonymous]
enabled = false

[auth.basic]
enabled = true
password_policy = true
```

> **TLS at the load balancer:** cookie_secure = true assumes users reach Grafana over HTTPS at the load balancer. Ensure the LB forwards X-Forwarded-Proto: https. If you must serve TLS on Grafana directly instead, set protocol = https, cert_file, and cert_key, then open 3000 only to approved sources.

## 8.4 Provision the Prometheus data source

Grafana queries the local Prometheus directly over loopback.

```bash
sudo tee /etc/grafana/provisioning/datasources/prometheus.yml >/dev/null <<'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://127.0.0.1:9090
    isDefault: true
    editable: false
EOF
```

## 8.5 Start Grafana

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now grafana-server
sudo systemctl status grafana-server --no-pager
curl -fsS http://127.0.0.1:3000/api/health
```

Expected: database status is `ok`. Review logs if startup fails:

```bash
sudo journalctl -u grafana-server --since "30 minutes ago" --no-pager
```

## 8.6 Firewall for Grafana

Allow TCP 3000 only from the organization load balancer or approved user network.

```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4"   source address="<APPROVED_CIDR>" port protocol="tcp" port="3000" accept'
sudo firewall-cmd --reload
```

# 9. External access, DNS, and load balancing

DNS and the load balancer are provided by the organization's network and platform teams and requested through the normal change process. Provide them the following so the request is unambiguous.

| Requested item | Value to supply |
| --- | --- |
| User-facing DNS name | <GRAFANA_FQDN> |
| Backend target | <MON_IP>:3000 (HTTP) |
| Protocol at the load balancer | HTTPS/443 with organization TLS certificate |
| Health check path | /api/health (expects HTTP 200) |
| Required forwarded header | X-Forwarded-Proto: https |
| Session affinity | Not required (single backend) |
| Allowed client networks | <APPROVED_CIDR> |

> **Validation after LB is live:** Confirm that https://<GRAFANA_FQDN>/ loads the Grafana login, the certificate is valid, and the load-balancer health check reports healthy against /api/health.

## 9.1 Initial login

Open `https://<GRAFANA_FQDN>/`. Sign in with `admin/admin`, then immediately replace the default password. Configure approved users and roles. If SSO is required, complete and test the organization's supported identity-provider integration before go-live.

# 10. Integrate application metrics

## 10.1 Linux host metrics

Install Node Exporter (Section 5) on each GitLab, Jenkins, SonarQube, and Nexus Linux server. Restrict port 9100 to the monitoring server IP address. Add each target to the Prometheus configuration.

## 10.2 GitLab Self-Managed

- Confirm the GitLab installation method and version.
- Use GitLab's built-in Prometheus metrics and bundled exporters where supported.
- Allow only the monitoring server address in the metrics allowlist.
- Do not expose unauthenticated exporters outside the monitoring network.
- Collect GitLab, Sidekiq, Gitaly, Workhorse, PostgreSQL, Redis, Registry, and node metrics as applicable.

## 10.3 Jenkins

- Install the Jenkins Prometheus Metrics plugin through the approved plugin process.
- Confirm the plugin supports the installed Jenkins controller version.
- Validate the default `/prometheus/` endpoint, including its required trailing slash.
- Use Jenkins authentication and network restrictions consistent with organizational policy.
- Validate job status, duration, executor, queue, JVM, and controller metrics before dashboard acceptance.

## 10.4 SonarQube

- Use `/api/monitoring/metrics` for supported operational metrics and secure it with the configured Sonar system passcode.
- Use `/api/measures` for project code-quality values and histories.
- Because code-quality API responses are not identical to ordinary Prometheus scraping, use an approved API exporter or collection process where required.
- Also collect CPU, memory, disk, and Java process metrics through Node Exporter and approved JMX collection.

## 10.5 Nexus Repository

- For Nexus Repository 3.81 or later, use `/service/rest/metrics/prometheus`.
- For earlier supported releases, validate `/service/metrics/prometheus`.
- Use a dedicated account with the `nx-metrics-all` privilege.
- Use synthetic HTTP checks for required artifact or repository availability because native instance metrics may not prove that a specific artifact can be downloaded.

## 10.6 Safe rollout procedure

1.  Enable one application endpoint at a time.

2.  Validate the endpoint locally on the application server.

3.  Validate network access from the monitoring server.

4.  Add the target to the Prometheus configuration.

5.  Run `promtool check config`.

6.  Reload Prometheus during the approved window.

7.  Confirm the target is `UP`.

8.  Validate metrics with the application owner before creating alerts.

# 11. Backups and recovery

> **Primary recovery control:** Backups are the recovery path for this platform. Treat backup success and restore rehearsals as go-live gates, not optional hardening.

## 11.1 What must be backed up

| Artifact | Backup method | Frequency |
| --- | --- | --- |
| Grafana PostgreSQL database | Nightly `pg_dump` into approved backup storage | Daily and before upgrades |
| PostgreSQL configuration | Protected file backup | After every approved change |
| Grafana configuration and provisioning | Protected backup and source control without secrets | After every change |
| Grafana plugins | Package/plugin inventory; reinstall from approved source | After plugin change |
| Prometheus/Alertmanager configuration | Private source control | After every change |
| Prometheus data | Optional TSDB snapshot if metric history must be retained | Policy dependent |
| Secrets and TLS material | PKI/secret-management system | According to policy |

## 11.2 PostgreSQL logical backup

Run using an approved protected path:

```bash
sudo -u postgres pg_dump   --format=custom   --file=<BACKUP_PATH>/grafana_$(date +%F_%H%M).dump   grafana

sudo -u postgres pg_restore --list   <BACKUP_PATH>/<GRAFANA_BACKUP_FILE>.dump | head
```

Copy backups off the monitoring server. A backup on the same failed host is not a recovery option.

## 11.3 Configuration backup

```bash
sudo tar --xattrs --selinux -czf   <BACKUP_PATH>/monitoring-config_$(date +%F_%H%M).tgz   /etc/grafana   /etc/prometheus   /etc/alertmanager   /etc/systemd/system/prometheus.service   /etc/systemd/system/alertmanager.service   /etc/systemd/system/node_exporter.service
```

> **Sensitive content:** The archive contains secrets and private configuration. Encrypt it, tightly restrict access, and never attach it to an ordinary ticket.

## 11.4 Restore test

- Perform a scheduled restore to a non-production PostgreSQL instance.
- Validate Grafana startup against the restored database.
- Confirm dashboards, users, data sources, and permissions.
- Record restoration time and compare it with the recovery-time objective.
- Correct the procedure after every failed or incomplete restore test.

## 11.5 Rebuild after host loss

1.  Provision a replacement RHEL 9 host and complete Sections 3 through 8.

2.  Before starting Grafana, restore the PostgreSQL database from the latest backup.

3.  Restore the configuration archive and reconcile secrets from the secret manager.

4.  Start services, confirm /api/health reports database `ok`, and validate dashboards.

5.  Request the load balancer to re-point <GRAFANA_FQDN> to the new host address.

# 12. Production validation and acceptance

## 12.1 Service validation

```bash
sudo systemctl is-active postgresql
sudo systemctl is-active prometheus
sudo systemctl is-active alertmanager
sudo systemctl is-active node_exporter
sudo systemctl is-active grafana-server

curl -fsS http://localhost:9090/-/ready
curl -fsS http://localhost:9093/-/ready
curl -fsS http://localhost:9100/metrics | head
curl -fsS http://127.0.0.1:3000/api/health
```

## 12.2 Acceptance checklist

- ☐ Prometheus shows all required targets as UP.
- ☐ Prometheus evaluates the expected alert-rule set without errors.
- ☐ Alertmanager is running and reachable on loopback 9093.
- ☐ A test alert is delivered and acknowledged through the approved notification channel.
- ☐ Grafana reports database status `ok` and loads the Prometheus data source.
- ☐ All monitoring services are enabled and return automatically after a reboot.
- ☐ Grafana is reachable through the organization load balancer at https://<GRAFANA_FQDN>/.
- ☐ The load-balancer TLS certificate is valid and the health check passes.
- ☐ Default administrator credentials have been replaced.
- ☐ Anonymous access and user self-registration are disabled.
- ☐ Exporter and application metrics ports are restricted to the monitoring server.
- ☐ Backups complete successfully and a restoration test has passed.
- ☐ The operations team has the runbook, ownership matrix, and escalation contacts.

## 12.3 Failure tests

| Test | Expected result | Evidence |
| --- | --- | --- |
| Stop then start Prometheus | systemd restarts it; scraping resumes. | Systemd status and Grafana query |
| Block one Node Exporter | TargetDown fires after configured delay. | Prometheus alert and notification |
| Reboot the monitoring server | All enabled services return automatically. | Systemd status and logs |
| Restore PostgreSQL backup | Grafana starts with expected data. | Restore record and screenshots |
| Simulate host loss rebuild | Platform is recovered within the RTO. | Timed rebuild record |

# 13. Operations, patching, and governance

## 13.1 Daily checks

- Target availability and scrape errors.
- Prometheus disk usage, ingestion rate, query latency, and rule failures.
- Alertmanager health and notification errors.
- PostgreSQL health and disk usage.
- Grafana health, failed logins, data-source errors, and certificate expiry (at the LB).
- Confirmation that the most recent backup completed and was copied off-host.

## 13.2 Upgrade sequence

1.  Review release notes, security advisories, compatibility, and rollback requirements.

2.  Back up PostgreSQL and all configuration files.

3.  Schedule an approved maintenance window; expect a monitoring outage during the upgrade.

4.  Upgrade one component at a time and validate before the next.

5.  Upgrade active Grafana only after a verified database backup.

6.  Do not downgrade Grafana without restoring the pre-upgrade database backup.

## 13.3 Configuration change sequence

```bash
sudo promtool check config /etc/prometheus/prometheus.yml
sudo promtool check rules /etc/prometheus/rules/*.yml
sudo amtool check-config /etc/alertmanager/alertmanager.yml
sudo systemctl reload-or-restart prometheus alertmanager
```

Validate configuration before reloading. Keep the previous known-good copy so a failed change can be reverted quickly.

## 13.4 Ownership

| Area | Primary owner | Required responsibilities |
| --- | --- | --- |
| RHEL and storage | Linux/platform team | Patching, capacity, filesystem, service recovery |
| PostgreSQL | Database/platform team | Backup, restore, capacity |
| Grafana | Monitoring team | Users, dashboards, provisioning, upgrades |
| Prometheus/Alertmanager | Monitoring team | Scrapes, rules, retention, notifications |
| Application endpoints | Application owners | Metrics enablement and version compatibility |
| Network/PKI/DNS/LB | Infrastructure teams | Firewall, certificates, names, load balancer |
| Incident response | Operations | Acknowledgment, escalation, runbook execution |

# Appendix A — Command and configuration inventory

| Component | Configuration | Data | Service |
| --- | --- | --- | --- |
| PostgreSQL | /var/lib/pgsql/data/*.conf | /var/lib/pgsql/data | postgresql |
| Grafana | /etc/grafana/grafana.ini | PostgreSQL database | grafana-server |
| Grafana provisioning | /etc/grafana/provisioning | N/A | grafana-server |
| Prometheus | /etc/prometheus | /u01/prometheus | prometheus |
| Alertmanager | /etc/alertmanager | /var/lib/alertmanager | alertmanager |
| Node Exporter | systemd unit | N/A | node_exporter |

# Appendix B — Troubleshooting quick reference

| Symptom | Checks |
| --- | --- |
| Grafana database error | Test PostgreSQL login on 127.0.0.1; inspect Grafana logs; verify password file, ssl_mode, and pg_hba.conf. |
| Grafana dashboard has no data | Check Prometheus readiness on 9090; confirm the data source URL is http://127.0.0.1:9090; inspect target status. |
| Prometheus will not start | Run promtool; check ownership, retention value, disk space, and systemd logs. |
| Target DOWN | Test the endpoint from the monitoring server; check firewall, authentication, certificate, and application health. |
| No notifications | Check Alertmanager health, the receiver configuration, and the approved channel credentials. |
| Grafana unreachable via URL | Confirm Grafana listens on 0.0.0.0:3000, firewall allows the LB, and the load balancer health check passes. |
| Login redirects to wrong scheme | Confirm root_url uses https and the LB forwards X-Forwarded-Proto: https. |

# Appendix C — Authoritative references

Grafana RHEL installation: https://grafana.com/docs/grafana/latest/setup-grafana/installation/redhat-rhel-fedora/

Grafana configuration: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/

Grafana database setup: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#database

Grafana backup: https://grafana.com/docs/grafana/latest/administration/back-up-grafana/

Prometheus downloads: https://prometheus.io/download/

Prometheus storage: https://prometheus.io/docs/prometheus/latest/storage/

Prometheus security model: https://prometheus.io/docs/operating/security/

Alertmanager configuration: https://prometheus.io/docs/alerting/latest/configuration/

RHEL 9 PostgreSQL installation: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_database_servers/using-postgresql_configuring-and-using-database-servers

PostgreSQL backup and restore: https://www.postgresql.org/docs/16/backup.html

GitLab Prometheus monitoring: https://docs.gitlab.com/administration/monitoring/prometheus/

Jenkins Prometheus plugin: https://plugins.jenkins.io/prometheus/

SonarQube Web API: https://docs.sonarsource.com/sonarqube-server/extension-guide/web-api

Nexus Prometheus metrics: https://help.sonatype.com/en/prometheus.html

> **Version note:** This runbook pins Prometheus 3.13.1 LTS (supported to 31 July 2027), Alertmanager 0.33.1, and Node Exporter 1.12.1, verified against the official release checksums on 23 July 2026. The earlier 3.5 LTS line reaches end of support on 31 July 2026 and should not be used for a new build. Revalidate versions and checksums immediately before production installation.
