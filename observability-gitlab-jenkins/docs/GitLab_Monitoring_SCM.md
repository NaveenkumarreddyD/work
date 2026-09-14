# GitLab Monitoring (SCM-only) — Design, Change Request & Config

**Context:** GitLab is self-managed **Omnibus** (Linux package), used **only as SCM**
(git hosting) — no CI/CD runners, no container registry in scope. Monitoring is
done with the existing Prometheus + Grafana + Alertmanager single-server stack.

**Goal:** know that developers can reach git, that Gitaly (the git engine) is
healthy, and that the repository disk is not filling — plus the supporting
services that keep those working.

---

## A. Placeholders

| Placeholder | Meaning | Example |
| --- | --- | --- |
| `<GITLAB_IP>` | GitLab server address | 10.10.10.20 |
| `<GITLAB_FQDN>` | GitLab URL host | gitlab.example.com |
| `<MON_IP>` | Your monitoring server | 10.10.10.11 |
| `<GIT_DATA_MOUNT>` | Filesystem holding git repos | /var/opt/gitlab |

---

## B. What GitLab exposes (bundled — nothing to install on GitLab)

Omnibus already runs these exporters; they just listen on 127.0.0.1 by default.

| Exporter | Port | Signal | Priority (SCM) |
| --- | --- | --- | --- |
| node_exporter | 9100 | Host CPU/mem/**disk** (repo storage) | **Tier 1** |
| gitaly | 9236 | Git RPC latency/errors — **the git engine** | **Tier 1** |
| gitlab-exporter | 9168 | Rails/DB/ring health | Tier 1 |
| workhorse | 9229 | HTTP git payloads, 5xx rates | Tier 2 |
| puma | 8083 | Web/API request rates + errors | Tier 2 |
| sidekiq | 8082 | Background jobs (mirroring, webhooks, housekeeping) | Tier 2 |
| postgres_exporter | 9187 | Bundled PostgreSQL | Tier 2 |
| redis_exporter | 9121 | Bundled Redis | Tier 2 |

---

## C. CHANGE REQUEST — send this to the GitLab platform owners

> Requesting the following on the GitLab Omnibus host so our central Prometheus
> (`<MON_IP>`) can scrape health metrics. These are read-only metrics endpoints;
> no application behavior changes. Access is restricted to the monitoring server
> by firewall.

### C.1 Edit `/etc/gitlab/gitlab.rb`

```ruby
# --- Allow the monitoring server to read health/metrics endpoints ---
gitlab_rails['monitoring_whitelist'] = ['127.0.0.0/8', '<MON_IP>/32']

# --- Tier 1: host + git engine + rails health ---
node_exporter['listen_address']    = '<GITLAB_IP>:9100'
gitlab_exporter['listen_address']  = '<GITLAB_IP>'
gitlab_exporter['listen_port']     = '9168'

# Gitaly metrics (GitLab 15.10+ hash syntax)
gitaly['configuration'] = {
  prometheus_listen_addr: '<GITLAB_IP>:9236',
}
# Older GitLab syntax if the above is rejected:
# gitaly['prometheus_listen_addr'] = '<GITLAB_IP>:9236'

# --- Tier 2: supporting services ---
gitlab_workhorse['prometheus_listen_addr'] = '<GITLAB_IP>:9229'
puma['exporter_enabled']       = true
puma['exporter_address']       = '<GITLAB_IP>'
puma['exporter_port']          = 8083
sidekiq['metrics_enabled']     = true
sidekiq['listen_address']      = '<GITLAB_IP>'
sidekiq['listen_port']         = 8082
postgres_exporter['listen_address'] = '<GITLAB_IP>:9187'
redis_exporter['listen_address']    = '<GITLAB_IP>:9121'
```

> **Note:** binding to `<GITLAB_IP>` (not `0.0.0.0`) plus the firewall rule in C.3
> keeps these endpoints reachable only on the internal network, then only from
> `<MON_IP>`. Do not expose them publicly.

### C.2 Apply

```bash
sudo gitlab-ctl reconfigure
```

### C.3 Firewall — allow ONLY the monitoring server

```bash
for p in 9100 9236 9168 9229 8083 8082 9187 9121; do
  sudo firewall-cmd --permanent --add-rich-rule="rule family=\"ipv4\" source address=\"<MON_IP>/32\" port protocol=\"tcp\" port=\"$p\" accept"
done
sudo firewall-cmd --reload
```

### C.4 Confirm (run on the GitLab host)

```bash
curl -s http://<GITLAB_IP>:9236/metrics | head    # gitaly
curl -s http://<GITLAB_IP>:9168/metrics | head    # gitlab-exporter
curl -s http://<GITLAB_IP>:9100/metrics | head    # node
```

### C.5 (Optional) Repo storage path — so we alert on the right disk

```bash
df -h /var/opt/gitlab/git-data   # tell us which filesystem/mount this is
```

---

## D. MONITORING SIDE — you own this (no GitLab access needed)

### D.1 Add scrape jobs to `/etc/prometheus/prometheus.yml`

Add under `scrape_configs:` (this is the deferred `application-linux-servers`
work, now made GitLab-specific). Start with Tier 1; add Tier 2 once exposed.

```yaml
  # --- GitLab (SCM) ---
  - job_name: gitlab-node
    static_configs:
      - targets: ['<GITLAB_IP>:9100']
        labels: { service: gitlab, role: host }

  - job_name: gitlab-gitaly
    static_configs:
      - targets: ['<GITLAB_IP>:9236']
        labels: { service: gitlab, role: gitaly }

  - job_name: gitlab-exporter
    static_configs:
      - targets: ['<GITLAB_IP>:9168']
        labels: { service: gitlab, role: rails }

  # Tier 2 (add after C exposes them)
  - job_name: gitlab-workhorse
    static_configs:
      - targets: ['<GITLAB_IP>:9229']
        labels: { service: gitlab, role: workhorse }
  - job_name: gitlab-puma
    static_configs:
      - targets: ['<GITLAB_IP>:8083']
        labels: { service: gitlab, role: puma }
  - job_name: gitlab-sidekiq
    static_configs:
      - targets: ['<GITLAB_IP>:8082']
        labels: { service: gitlab, role: sidekiq }
  - job_name: gitlab-postgres
    static_configs:
      - targets: ['<GITLAB_IP>:9187']
        labels: { service: gitlab, role: postgres }
  - job_name: gitlab-redis
    static_configs:
      - targets: ['<GITLAB_IP>:9121']
        labels: { service: gitlab, role: redis }
```

Validate + reload:

```bash
sudo promtool check config /etc/prometheus/prometheus.yml
sudo systemctl reload-or-restart prometheus
```

Then confirm every target is UP in Prometheus (Status → Targets), or:

```bash
curl -s 'http://127.0.0.1:9090/api/v1/query?query=up{service="gitlab"}'
```

### D.2 SCM-focused alert rules — `/etc/prometheus/rules/gitlab.yml`

> Metric names can vary slightly by GitLab version — after scraping starts,
> confirm each metric exists in the target's `/metrics` before trusting the rule.

```yaml
groups:
  - name: gitlab-scm
    rules:
      # Any GitLab component unreachable = git may be down
      - alert: GitLabComponentDown
        expr: up{service="gitlab"} == 0
        for: 5m
        labels: { severity: critical }
        annotations:
          summary: "GitLab component down: {{ $labels.job }} ({{ $labels.instance }})"
          description: "Prometheus cannot scrape this GitLab component for 5m."

      # Repository storage filling — pushes fail when this hits 0
      - alert: GitLabRepoDiskLow
        expr: 100 * node_filesystem_avail_bytes{service="gitlab",mountpoint="<GIT_DATA_MOUNT>"}
              / node_filesystem_size_bytes{service="gitlab",mountpoint="<GIT_DATA_MOUNT>"} < 15
        for: 15m
        labels: { severity: critical }
        annotations:
          summary: "GitLab repo disk <15% free on {{ $labels.instance }}"

      # Gitaly returning git RPC errors (clone/push/pull failing)
      - alert: GitalyErrors
        expr: sum by (grpc_method) (rate(grpc_server_handled_total{job="gitlab-gitaly",grpc_code!="OK"}[5m])) > 0
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "Gitaly errors on {{ $labels.grpc_method }}"
          description: "Git RPCs are failing; developers may see clone/push errors."

      # Gitaly slow (p99 RPC latency high)
      - alert: GitalyHighLatency
        expr: histogram_quantile(0.99, sum by (le) (rate(grpc_server_handling_seconds_bucket{job="gitlab-gitaly"}[5m]))) > 1
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "Gitaly p99 git RPC latency > 1s"

      # Web/API 5xx (HTTPS git + UI failing) — from workhorse
      - alert: GitLab5xxErrors
        expr: sum(rate(gitlab_workhorse_http_requests_total{job="gitlab-workhorse",code=~"5.."}[5m])) > 0.1
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "GitLab serving 5xx responses"

      # Background job backlog (mirroring/webhooks/housekeeping stuck)
      - alert: GitLabSidekiqBacklog
        expr: sum(sidekiq_queue_size{job="gitlab-sidekiq"}) > 1000
        for: 15m
        labels: { severity: warning }
        annotations:
          summary: "GitLab Sidekiq backlog > 1000 jobs"
```

```bash
sudo promtool check rules /etc/prometheus/rules/gitlab.yml
sudo systemctl reload-or-restart prometheus
```

### D.3 (Optional but recommended) Black-box "can a dev actually reach git?"

The exporters tell you services are *running*; a black-box probe tells you the
**front door works** (HTTPS 443 + SSH 22). This is the truest SCM signal and
needs **no GitLab access** — it runs on the monitoring server.

```bash
# On the monitoring server (blackbox_exporter 0.28.0):
cd /tmp
curl -fLO https://github.com/prometheus/blackbox_exporter/releases/download/v0.28.0/blackbox_exporter-0.28.0.linux-amd64.tar.gz
echo "caf5d242fb1cf6d5cb678f3f799f22703d4fafea26b03dcbbd7e1f1825e06329  blackbox_exporter-0.28.0.linux-amd64.tar.gz" | sha256sum -c -
tar -xzf blackbox_exporter-0.28.0.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin blackbox_exporter
sudo install -d -o blackbox_exporter -g blackbox_exporter -m 0750 /etc/blackbox_exporter
sudo install -m 0755 blackbox_exporter-0.28.0.linux-amd64/blackbox_exporter /usr/local/bin/blackbox_exporter
sudo tee /etc/blackbox_exporter/blackbox.yml >/dev/null <<'EOF'
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http: { method: GET, valid_status_codes: [200], preferred_ip_protocol: ip4 }
  tcp_connect:
    prober: tcp
    timeout: 5s
EOF
sudo chown -R blackbox_exporter:blackbox_exporter /etc/blackbox_exporter
# systemd unit -> ExecStart=/usr/local/bin/blackbox_exporter --config.file=/etc/blackbox_exporter/blackbox.yml --web.listen-address=127.0.0.1:9115
# (full unit is in the command sheet Section 14 and runbook Section 14.3)
sudo systemctl daemon-reload && sudo systemctl enable --now blackbox_exporter
```

Prometheus jobs:

```yaml
  - job_name: gitlab-blackbox-ssh
    metrics_path: /probe
    params: { module: [tcp_connect] }
    static_configs:
      - targets: ['<GITLAB_IP>:22']
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 127.0.0.1:9115

  - job_name: gitlab-blackbox-https
    metrics_path: /probe
    params: { module: [http_2xx] }
    static_configs:
      - targets: ['https://<GITLAB_FQDN>/-/readiness']
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 127.0.0.1:9115
```

Alert:

```yaml
      - alert: GitLabUnreachable
        expr: probe_success{job=~"gitlab-blackbox.*"} == 0
        for: 3m
        labels: { severity: critical }
        annotations:
          summary: "GitLab front door down: {{ $labels.instance }}"
```

---

## E. Grafana dashboards

Data source = your existing **Prometheus** (not the GitLab datasource plugin).

- Import GitLab's official dashboards (search grafana.com for "GitLab Omnibus"
  / "Gitaly"), or build panels from these key queries:
  - Git RPC rate: `sum(rate(grpc_server_handled_total{job="gitlab-gitaly"}[5m])) by (grpc_method)`
  - Git RPC errors: `sum(rate(grpc_server_handled_total{job="gitlab-gitaly",grpc_code!="OK"}[5m]))`
  - Repo disk free %: `100 * node_filesystem_avail_bytes{service="gitlab",mountpoint="<GIT_DATA_MOUNT>"} / node_filesystem_size_bytes{...}`
  - Component up/down: `up{service="gitlab"}`
  - Web 5xx: `sum(rate(gitlab_workhorse_http_requests_total{code=~"5.."}[5m]))`
  - Sidekiq backlog: `sum(sidekiq_queue_size{job="gitlab-sidekiq"})`
- After import, set the dashboard variable/data source to **Prometheus**.

---

## F. Acceptance checklist

- [ ] GitLab owners applied C.1–C.3 and `reconfigure` succeeded.
- [ ] All `gitlab-*` targets show **UP** in Prometheus.
- [ ] `GitLabComponentDown` tested (stop one exporter → alert fires → notification).
- [ ] Repo disk alert points at the correct `<GIT_DATA_MOUNT>` (confirmed via `df`).
- [ ] Black-box HTTPS + SSH probes succeed (`probe_success == 1`).
- [ ] Grafana dashboard renders git RPC, disk, and component health.
- [ ] A test SSH clone and HTTPS clone both succeed while dashboards show traffic.

---

## What this deliberately does NOT monitor

Out of scope because GitLab is SCM-only here: CI/CD pipeline metrics, runner
fleet, container registry, DORA/engineering-activity metrics (that's what the
GitLab *API datasource* is for — not needed). Add later only if usage expands.
