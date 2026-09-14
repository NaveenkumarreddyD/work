#!/usr/bin/env bash
###############################################################################
# Grafana Monitoring Platform - Single-Server Production Install
# COMMAND SHEET (copy-paste friendly companion to the runbook .docx)
#
# RHEL 9 | Grafana OSS | PostgreSQL 16 | Prometheus 3.13.1 LTS
#         | Alertmanager 0.33.1 | Node Exporter 1.12.1
#
# HOW TO USE:
#   - Every executable command is on ONE line (URLs are not split), so copy
#     safely without backslash/line-wrap breakage.
#   - Lines starting with #  are notes, NOT commands - do not paste them.
#   - Run steps IN ORDER. This is a reference, not an unattended installer;
#     read each block and confirm output before moving on.
#   - Config-file blocks use  tee <<'EOF' ... EOF  and paste as one unit.
#
# REPLACE THESE PLACEHOLDERS EVERYWHERE BEFORE RUNNING:
#   <MON_IP>           e.g. 10.10.10.11    (this monitoring server)
#   <GRAFANA_FQDN>     e.g. grafana.example.com
#   <APPROVED_CIDR>    e.g. 10.20.0.0/16   (LB / user network allowed to :3000)
#   <PROM_RETENTION_SIZE>   40GB           (~80% of the 50 GB /u01 mount)
#   <GITLAB_SERVER> <JENKINS_SERVER> <SONARQUBE_SERVER> <NEXUS_SERVER>
###############################################################################


###############################################################################
# 3. BASE RHEL 9 PREPARATION
###############################################################################

# 3.1 Confirm the host (read-only checks)
cat /etc/redhat-release
uname -m
hostname -f
df -h
free -h
timedatectl
chronyc tracking

# 3.1 Update + base packages, then reboot (schedule/approve first)
sudo dnf update -y
sudo dnf install -y curl wget tar gzip unzip vim policycoreutils-python-utils
sudo systemctl reboot

# 3.2 Verify the /u01 mount and create data / backup directories
findmnt /u01
df -hT /u01
sudo install -d -o root -g root -m 0755 /u01/prometheus
sudo install -d -o root -g root -m 0750 /var/backups/monitoring
sudo install -d -o root -g root -m 0755 /etc/monitoring

# 3.3 Confirm SELinux (want: Enforcing) and firewall (want: running)
getenforce
sudo firewall-cmd --state
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --get-default-zone


###############################################################################
# 4. INSTALL POSTGRESQL 16  (Grafana backend, loopback only)
###############################################################################

# 4.1 Install packages
sudo dnf module reset postgresql -y
sudo dnf module install postgresql:16/server -y
postgres --version

# 4.2 Initialize the data directory WITH checksums (one line - do not split)
sudo PGSETUP_INITDB_OPTIONS="--data-checksums" postgresql-setup --initdb

# 4.2 Confirm checksums enabled (expect a non-zero version number)
sudo -u postgres pg_controldata /var/lib/pgsql/data | grep "Data page checksum"

# 4.3 Append the tuning/security overrides to postgresql.conf (last value wins)
sudo tee -a /var/lib/pgsql/data/postgresql.conf >/dev/null <<'EOF'

# --- Grafana monitoring platform (single-server) overrides ---
listen_addresses = 'localhost'
port = 5432
password_encryption = 'scram-sha-256'
max_connections = 200
shared_buffers = '512MB'
log_connections = on
log_disconnections = on
log_line_prefix = '%m [%p] %u@%d %r '
EOF

# 4.3 Append loopback-only, SCRAM access for the grafana role to pg_hba.conf
sudo tee -a /var/lib/pgsql/data/pg_hba.conf >/dev/null <<'EOF'
host  grafana  grafana  127.0.0.1/32  scram-sha-256
host  grafana  grafana  ::1/128       scram-sha-256
EOF

# 4.4 Start PostgreSQL and confirm it is running
sudo systemctl enable --now postgresql
sudo systemctl status postgresql --no-pager
sudo -u postgres psql -c "SELECT version();"

# 4.4 Create the grafana role + database.
#     Run the next line, then paste the four SQL lines at the postgres=# prompt.
#     You will be prompted to set the grafana password by \password.
sudo -u postgres psql
# CREATE ROLE grafana LOGIN;
# \password grafana
# CREATE DATABASE grafana OWNER grafana ENCODING 'UTF8' TEMPLATE template0;
# \q

# 4.5 Verify connectivity (prompts for the grafana password, returns "grafana")
psql "host=127.0.0.1 port=5432 dbname=grafana user=grafana" -c "SELECT current_database();"


###############################################################################
# 5. INSTALL NODE EXPORTER  (this server AND every application server)
###############################################################################

# 5.1 Download + verify checksum + install (each command is one line)
cd /tmp
curl -fLO https://github.com/prometheus/node_exporter/releases/download/v1.12.1/node_exporter-1.12.1.linux-amd64.tar.gz
echo "b51d8a76aa2a9156a55d501aca6276fae09e262259a5e4e831d2c2222f084e63  node_exporter-1.12.1.linux-amd64.tar.gz" | sha256sum -c -
tar -xzf node_exporter-1.12.1.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin node_exporter
sudo install -m 0755 node_exporter-1.12.1.linux-amd64/node_exporter /usr/local/bin/node_exporter

# 5.2 Create the systemd service (paste the whole tee block)
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

# 5.3 Firewall - ONLY on application servers (not needed on this host: loopback)
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="<MON_IP>/32" port protocol="tcp" port="9100" accept'
sudo firewall-cmd --reload


###############################################################################
# 6. INSTALL PROMETHEUS 3.13.1 LTS  (data on /u01)
###############################################################################

# 6.1 Download + verify + install
cd /tmp
curl -fLO https://github.com/prometheus/prometheus/releases/download/v3.13.1/prometheus-3.13.1.linux-amd64.tar.gz
echo "962b812371aff838d152b6ff2d56fdb7a6396f5542f48ebf73421b9721f0d103  prometheus-3.13.1.linux-amd64.tar.gz" | sha256sum -c -
tar -xzf prometheus-3.13.1.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin prometheus
sudo install -d -o prometheus -g prometheus -m 0750 /etc/prometheus /etc/prometheus/rules
sudo chown prometheus:prometheus /u01/prometheus
sudo chmod 0750 /u01/prometheus
sudo restorecon -Rv /u01/prometheus
sudo install -m 0755 prometheus-3.13.1.linux-amd64/prometheus /usr/local/bin/prometheus
sudo install -m 0755 prometheus-3.13.1.linux-amd64/promtool /usr/local/bin/promtool

# 6.2 Prometheus config.
#     Application targets are OMITTED for now (details not available yet).
#     This config monitors Prometheus itself + the local Node Exporter, which
#     is enough to start the service. Add the app job later (see 6.2-LATER).
sudo tee /etc/prometheus/prometheus.yml >/dev/null <<'EOF'
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

  # 6.2-LATER: once you have the application server addresses, uncomment this
  # block, fill in the real hostnames/IPs, then re-run 6.4 and reload:
  #   sudo promtool check config /etc/prometheus/prometheus.yml
  #   sudo systemctl reload-or-restart prometheus
  # - job_name: application-linux-servers
  #   static_configs:
  #     - targets:
  #         - <GITLAB_SERVER>:9100
  #         - <JENKINS_SERVER>:9100
  #         - <SONARQUBE_SERVER>:9100
  #         - <NEXUS_SERVER>:9100
EOF

# 6.3 Initial alert rules  (OPTIONAL, but recommended even with no app servers:
#     every rule below applies to THIS monitoring host via its local Node
#     Exporter, so it protects your single-server box from day one. To defer,
#     just do not run this tee block - Prometheus starts fine with no rules.)
sudo tee /etc/prometheus/rules/infrastructure.yml >/dev/null <<'EOF'
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
        expr: 100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"

      - alert: HostLowMemory
        expr: (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 < 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Available memory below 10% on {{ $labels.instance }}"

      - alert: HostFilesystemLow
        expr: 100 * node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"} < 15
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Filesystem space below 15% on {{ $labels.instance }}"
EOF

# 6.4 Fix ownership and validate config (+ rules only if 6.3 was done)
sudo chown -R prometheus:prometheus /etc/prometheus /u01/prometheus
sudo promtool check config /etc/prometheus/prometheus.yml
ls /etc/prometheus/rules/*.yml >/dev/null 2>&1 && sudo promtool check rules /etc/prometheus/rules/*.yml || echo "No rule files yet - skipping rules check"

# 6.5 Create the systemd service.
#     IMPORTANT: replace <PROM_RETENTION_SIZE> with 40GB before pasting.
sudo tee /etc/systemd/system/prometheus.service >/dev/null <<'EOF'
[Unit]
Description=Prometheus Monitoring Server
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/u01/prometheus \
  --storage.tsdb.retention.time=30d \
  --storage.tsdb.retention.size=<PROM_RETENTION_SIZE> \
  --web.listen-address=127.0.0.1:9090
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


###############################################################################
# 7. INSTALL ALERTMANAGER 0.33.1  (single node)
###############################################################################

# 7.1 Download + verify + install
cd /tmp
curl -fLO https://github.com/prometheus/alertmanager/releases/download/v0.33.1/alertmanager-0.33.1.linux-amd64.tar.gz
echo "93d802cba6a8d27239d747ce117df7648d326ab67394e32247540b030e9842ba  alertmanager-0.33.1.linux-amd64.tar.gz" | sha256sum -c -
tar -xzf alertmanager-0.33.1.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin alertmanager
sudo install -d -o alertmanager -g alertmanager -m 0750 /etc/alertmanager /var/lib/alertmanager
sudo install -m 0755 alertmanager-0.33.1.linux-amd64/alertmanager /usr/local/bin/alertmanager
sudo install -m 0755 alertmanager-0.33.1.linux-amd64/amtool /usr/local/bin/amtool

# 7.2 Routing config (replace the placeholder receiver before go-live)
sudo tee /etc/alertmanager/alertmanager.yml >/dev/null <<'EOF'
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
EOF

# 7.3 Validate
sudo chown -R alertmanager:alertmanager /etc/alertmanager /var/lib/alertmanager
sudo amtool check-config /etc/alertmanager/alertmanager.yml

# 7.4 Create the systemd service (clustering disabled via empty cluster addr)
sudo tee /etc/systemd/system/alertmanager.service >/dev/null <<'EOF'
[Unit]
Description=Prometheus Alertmanager
Wants=network-online.target
After=network-online.target

[Service]
User=alertmanager
Group=alertmanager
Type=simple
ExecStart=/usr/local/bin/alertmanager \
  --config.file=/etc/alertmanager/alertmanager.yml \
  --storage.path=/var/lib/alertmanager \
  --web.listen-address=127.0.0.1:9093 \
  --cluster.listen-address=
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


###############################################################################
# 8. INSTALL GRAFANA OSS
###############################################################################

# 8.1 Add the official Grafana RPM repo and install
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

# 8.2 Create secret files (then put real values in with vi; keep 0640 perms)
sudo install -d -o root -g grafana -m 0750 /etc/grafana/secrets
sudo vi /etc/grafana/secrets/postgres_password
sudo vi /etc/grafana/secrets/secret_key
sudo chown root:grafana /etc/grafana/secrets/*
sudo chmod 0640 /etc/grafana/secrets/*

# 8.3 Configure Grafana - EDIT /etc/grafana/grafana.ini MANUALLY.
#     grafana.ini already has [database]/[server]/[security] sections with
#     defaults, so DO NOT blindly append. Open it and set these keys under the
#     matching sections (replace <GRAFANA_FQDN>):
sudo vi /etc/grafana/grafana.ini
# [database]
# type = postgres
# host = 127.0.0.1:5432
# name = grafana
# user = grafana
# password = $__file{/etc/grafana/secrets/postgres_password}
# ssl_mode = disable
# max_idle_conn = 10
# max_open_conn = 100
# conn_max_lifetime = 3600
# migration_locking = true
# locking_attempt_timeout_sec = 60
#
# [server]
# protocol = http
# http_addr = 0.0.0.0
# http_port = 3000
# domain = <GRAFANA_FQDN>
# root_url = https://<GRAFANA_FQDN>/
# enforce_domain = false
#
# [security]
# secret_key = $__file{/etc/grafana/secrets/secret_key}
# cookie_secure = true
# cookie_samesite = strict
#
# [users]
# allow_sign_up = false
#
# [auth.anonymous]
# enabled = false
#
# [auth.basic]
# enabled = true
# password_policy = true

# 8.4 Provision the Prometheus data source (points at local Prometheus)
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

# 8.5 Start Grafana (expect: database status "ok")
sudo systemctl daemon-reload
sudo systemctl enable --now grafana-server
sudo systemctl status grafana-server --no-pager
curl -fsS http://127.0.0.1:3000/api/health
# If it fails: sudo journalctl -u grafana-server --since "30 minutes ago" --no-pager

# 8.6 Firewall - allow :3000 only from the org LB / approved network
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="<APPROVED_CIDR>" port protocol="tcp" port="3000" accept'
sudo firewall-cmd --reload


###############################################################################
# 9. EXTERNAL ACCESS (DNS + LOAD BALANCER) - organization-provided
###############################################################################
# Give the network/platform team:
#   DNS name         : <GRAFANA_FQDN>
#   Backend target   : <MON_IP>:3000  (HTTP)
#   LB protocol      : HTTPS/443 with org TLS certificate (terminates TLS)
#   Health check     : /api/health  (expects HTTP 200)
#   Forwarded header : X-Forwarded-Proto: https
#   Allowed networks : <APPROVED_CIDR>
# Then browse https://<GRAFANA_FQDN>/  -> log in admin/admin -> change password.


###############################################################################
# 11. BACKUPS  (replace <BACKUP_PATH>, keep backups OFF this host)
###############################################################################

# 11.2 PostgreSQL logical backup
sudo -u postgres pg_dump --format=custom --file=<BACKUP_PATH>/grafana_$(date +%F_%H%M).dump grafana

# 11.3 Configuration backup (encrypt + restrict access afterwards)
sudo tar --xattrs --selinux -czf <BACKUP_PATH>/monitoring-config_$(date +%F_%H%M).tgz /etc/grafana /etc/prometheus /etc/alertmanager /etc/systemd/system/prometheus.service /etc/systemd/system/alertmanager.service /etc/systemd/system/node_exporter.service


###############################################################################
# 12. VALIDATION
###############################################################################
sudo systemctl is-active postgresql prometheus alertmanager node_exporter grafana-server
curl -fsS http://localhost:9090/-/ready
curl -fsS http://localhost:9093/-/ready
curl -fsS http://localhost:9100/metrics | head
curl -fsS http://127.0.0.1:3000/api/health

# 13.3 Re-validate before any future config change
sudo promtool check config /etc/prometheus/prometheus.yml
sudo promtool check rules /etc/prometheus/rules/*.yml
sudo amtool check-config /etc/alertmanager/alertmanager.yml
sudo systemctl reload-or-restart prometheus alertmanager


###############################################################################
# 14. INSTALL BLACKBOX EXPORTER  (front-door HTTPS/SSH probes, on THIS server)
###############################################################################

# 14.1 Download + verify + install (blackbox_exporter 0.28.0)
cd /tmp
curl -fLO https://github.com/prometheus/blackbox_exporter/releases/download/v0.28.0/blackbox_exporter-0.28.0.linux-amd64.tar.gz
echo "caf5d242fb1cf6d5cb678f3f799f22703d4fafea26b03dcbbd7e1f1825e06329  blackbox_exporter-0.28.0.linux-amd64.tar.gz" | sha256sum -c -
tar -xzf blackbox_exporter-0.28.0.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin blackbox_exporter
sudo install -d -o blackbox_exporter -g blackbox_exporter -m 0750 /etc/blackbox_exporter
sudo install -m 0755 blackbox_exporter-0.28.0.linux-amd64/blackbox_exporter /usr/local/bin/blackbox_exporter

# 14.2 Probe modules
sudo tee /etc/blackbox_exporter/blackbox.yml >/dev/null <<'EOF'
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      method: GET
      valid_status_codes: [200]
      preferred_ip_protocol: ip4
  tcp_connect:
    prober: tcp
    timeout: 5s
EOF

# 14.3 Service (binds to loopback; only Prometheus queries it)
sudo chown -R blackbox_exporter:blackbox_exporter /etc/blackbox_exporter
sudo tee /etc/systemd/system/blackbox_exporter.service >/dev/null <<'EOF'
[Unit]
Description=Prometheus Blackbox Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=blackbox_exporter
Group=blackbox_exporter
Type=simple
ExecStart=/usr/local/bin/blackbox_exporter --config.file=/etc/blackbox_exporter/blackbox.yml --web.listen-address=127.0.0.1:9115
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
sudo systemctl enable --now blackbox_exporter
sudo systemctl status blackbox_exporter --no-pager


###############################################################################
# 15. GITLAB (SCM) MONITORING
###############################################################################
#
# STEP 1 (GitLab owners, NOT this host): send them Section 15.2 of the runbook
#        (the /etc/gitlab/gitlab.rb change request) so the bundled exporters are
#        exposed to <MON_IP>. Nothing to install on GitLab.
#
# STEP 2 (this host): add the GitLab scrape jobs. prometheus.yml already exists,
#        so DO NOT append blindly - open it and paste the block below under the
#        existing "scrape_configs:" key (replace <GITLAB_IP> / <GITLAB_FQDN>).
sudo vi /etc/prometheus/prometheus.yml
#   - job_name: gitlab-node
#     static_configs: [ { targets: ['<GITLAB_IP>:9100'], labels: { service: gitlab, role: host } } ]
#   - job_name: gitlab-gitaly
#     static_configs: [ { targets: ['<GITLAB_IP>:9236'], labels: { service: gitlab, role: gitaly } } ]
#   - job_name: gitlab-exporter
#     static_configs: [ { targets: ['<GITLAB_IP>:9168'], labels: { service: gitlab, role: rails } } ]
#   # Tier 2 (add after they are exposed):
#   - job_name: gitlab-workhorse
#     static_configs: [ { targets: ['<GITLAB_IP>:9229'], labels: { service: gitlab, role: workhorse } } ]
#   - job_name: gitlab-puma
#     static_configs: [ { targets: ['<GITLAB_IP>:8083'], labels: { service: gitlab, role: puma } } ]
#   - job_name: gitlab-sidekiq
#     static_configs: [ { targets: ['<GITLAB_IP>:8082'], labels: { service: gitlab, role: sidekiq } } ]
#   - job_name: gitlab-postgres
#     static_configs: [ { targets: ['<GITLAB_IP>:9187'], labels: { service: gitlab, role: postgres } } ]
#   - job_name: gitlab-redis
#     static_configs: [ { targets: ['<GITLAB_IP>:9121'], labels: { service: gitlab, role: redis } } ]
#   # Front-door probes (needs Section 14 blackbox exporter):
#   - job_name: gitlab-blackbox-ssh
#     metrics_path: /probe
#     params: { module: [tcp_connect] }
#     static_configs: [ { targets: ['<GITLAB_IP>:22'] } ]
#     relabel_configs:
#       - { source_labels: [__address__], target_label: __param_target }
#       - { source_labels: [__param_target], target_label: instance }
#       - { target_label: __address__, replacement: 127.0.0.1:9115 }
#   - job_name: gitlab-blackbox-https
#     metrics_path: /probe
#     params: { module: [http_2xx] }
#     static_configs: [ { targets: ['https://<GITLAB_FQDN>/-/readiness'] } ]
#     relabel_configs:
#       - { source_labels: [__address__], target_label: __param_target }
#       - { source_labels: [__param_target], target_label: instance }
#       - { target_label: __address__, replacement: 127.0.0.1:9115 }

# STEP 3 (this host): SCM alert rules. Replace <GIT_DATA_MOUNT> (from the GitLab
#        team's `df -h /var/opt/gitlab/git-data`) before pasting.
sudo tee /etc/prometheus/rules/gitlab.yml >/dev/null <<'EOF'
groups:
  - name: gitlab-scm
    rules:
      - alert: GitLabComponentDown
        expr: up{service="gitlab"} == 0
        for: 5m
        labels: { severity: critical }
        annotations:
          summary: "GitLab component down: {{ $labels.job }} ({{ $labels.instance }})"

      - alert: GitLabRepoDiskLow
        expr: 100 * node_filesystem_avail_bytes{service="gitlab",mountpoint="<GIT_DATA_MOUNT>"} / node_filesystem_size_bytes{service="gitlab",mountpoint="<GIT_DATA_MOUNT>"} < 15
        for: 15m
        labels: { severity: critical }
        annotations:
          summary: "GitLab repo disk <15% free on {{ $labels.instance }}"

      - alert: GitalyErrors
        expr: sum by (grpc_method) (rate(grpc_server_handled_total{job="gitlab-gitaly",grpc_code!="OK"}[5m])) > 0
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "Gitaly errors on {{ $labels.grpc_method }} (clone/push may fail)"

      - alert: GitalyHighLatency
        expr: histogram_quantile(0.99, sum by (le) (rate(grpc_server_handling_seconds_bucket{job="gitlab-gitaly"}[5m]))) > 1
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "Gitaly p99 git RPC latency > 1s"

      - alert: GitLab5xxErrors
        expr: sum(rate(gitlab_workhorse_http_requests_total{job="gitlab-workhorse",code=~"5.."}[5m])) > 0.1
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "GitLab serving 5xx responses"

      - alert: GitLabSidekiqBacklog
        expr: sum(sidekiq_queue_size{job="gitlab-sidekiq"}) > 1000
        for: 15m
        labels: { severity: warning }
        annotations:
          summary: "GitLab Sidekiq backlog > 1000 jobs"

      - alert: GitLabUnreachable
        expr: probe_success{job=~"gitlab-blackbox.*"} == 0
        for: 3m
        labels: { severity: critical }
        annotations:
          summary: "GitLab front door down: {{ $labels.instance }}"
EOF

# STEP 4 (this host): validate + reload, then confirm targets + probes
sudo promtool check config /etc/prometheus/prometheus.yml
sudo promtool check rules /etc/prometheus/rules/gitlab.yml
sudo systemctl reload-or-restart prometheus
curl -s 'http://127.0.0.1:9090/api/v1/query?query=up{service="gitlab"}'
curl -s 'http://127.0.0.1:9115/probe?target=<GITLAB_IP>:22&module=tcp_connect' | grep probe_success
curl -s 'http://127.0.0.1:9115/probe?target=https://<GITLAB_FQDN>/-/readiness&module=http_2xx' | grep probe_success
