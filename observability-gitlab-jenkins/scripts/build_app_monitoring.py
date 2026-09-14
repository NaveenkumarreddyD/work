from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT = Path("/Users/naveendubba/Documents/Ibm mas and manage/"
           "App_Monitoring_GitLab_Jenkins_EndToEnd.docx")

BLUE = "1F4E78"; BLUE2 = "2E74B5"; DARK = "1F2937"; MUTED = "667085"
LIGHT_BLUE = "E8EEF5"; CODE_FILL = "F5F7FA"; CAUTION_FILL = "FFF4CE"
RISK_FILL = "FDECEC"; GREEN_FILL = "EAF5EA"
TABLE_WIDTH = 9360; TABLE_INDENT = 120


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd"); tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar"); tc_pr.append(tc_mar)
    for m, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}"); tc_mar.append(node)
        node.set(qn("w:w"), str(value)); node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths):
    assert sum(widths) == TABLE_WIDTH
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW"); tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(TABLE_WIDTH)); tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd"); tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(TABLE_INDENT)); tbl_ind.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol"); col.set(qn("w:w"), str(width)); grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW"); tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths[idx])); tc_w.set(qn("w:type"), "dxa")
            cell.width = Inches(widths[idx] / 1440)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); tr_pr.append(h)


def set_run_font(run, name="Calibri", size=11, bold=None, italic=None, color=DARK):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None: run.bold = bold
    if italic is not None: run.italic = italic


def set_para_border_bottom(paragraph, color=BLUE, size=10, space=4):
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr"); p_pr.append(p_bdr)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), str(space)); bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)


def shade_paragraph(paragraph, fill):
    p_pr = paragraph._p.get_or_add_pPr()
    shd = p_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd"); p_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_text(cell, text, bold=False, color=DARK, size=9.5, align=WD_ALIGN_PARAGRAPH.LEFT):
    p = cell.paragraphs[0]; p.alignment = align
    p.paragraph_format.space_before = Pt(0); p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.1
    r = p.add_run(text); set_run_font(r, size=size, bold=bold, color=color)


def add_table(doc, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers)); table.style = "Table Grid"
    set_table_geometry(table, widths)
    header = table.rows[0]; set_repeat_table_header(header)
    for idx, text in enumerate(headers):
        set_cell_shading(header.cells[idx], LIGHT_BLUE)
        set_cell_text(header.cells[idx], text, bold=True, color=BLUE, size=9.2)
    for row_data in rows:
        row = table.add_row()
        for idx, text in enumerate(row_data):
            set_cell_text(row.cells[idx], str(text), size=9.2)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_code(doc, text):
    p = doc.add_paragraph(style="Code Block"); p.paragraph_format.keep_together = True
    shade_paragraph(p, CODE_FILL)
    r = p.add_run(text.strip("\n")); set_run_font(r, name="Consolas", size=8.2, color="202124")
    return p


def add_callout(doc, label, text, kind="note"):
    fill = {"note": LIGHT_BLUE, "warning": CAUTION_FILL, "risk": RISK_FILL, "success": GREEN_FILL}[kind]
    p = doc.add_paragraph(style="Callout"); shade_paragraph(p, fill)
    r = p.add_run(f"{label}: "); set_run_font(r, size=10.2, bold=True, color=BLUE if kind != "risk" else "9B1C1C")
    r = p.add_run(text); set_run_font(r, size=10.2, color=DARK)
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.paragraph_format.left_indent = Inches(0.375 + level * 0.25)
    p.paragraph_format.first_line_indent = Inches(-0.188)
    p.paragraph_format.space_after = Pt(4); p.paragraph_format.line_spacing = 1.25
    r = p.add_run(text); set_run_font(r, size=10.5)
    return p


def add_number(doc, text, number):
    p = doc.add_paragraph(style="Normal")
    p.paragraph_format.left_indent = Inches(0.375)
    p.paragraph_format.first_line_indent = Inches(-0.188)
    p.paragraph_format.space_after = Pt(4); p.paragraph_format.line_spacing = 1.25
    r = p.add_run(f"{number}.  {text}"); set_run_font(r, size=10.5)
    return p


def add_body(doc, text):
    p = doc.add_paragraph(style="Normal")
    r = p.add_run(text); set_run_font(r)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(text, style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    return p


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page "); set_run_font(run, size=9, color=MUTED)
    for t, v in (("begin", None), ("instr", "PAGE"), ("end", None)):
        if t == "instr":
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = v
        else:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), t)
        run._r.append(el)


def configure_styles(doc):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11); normal.font.color.rgb = RGBColor.from_string(DARK)
    normal.paragraph_format.space_before = Pt(0); normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25
    for name, (size, color, before, after) in {
        "Heading 1": (16, BLUE2, 18, 10),
        "Heading 2": (13, BLUE2, 14, 7),
        "Heading 3": (12, BLUE, 10, 5),
    }.items():
        style = styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size); style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
    code = styles.add_style("Code Block", 1)
    code.font.name = "Consolas"
    code._element.rPr.rFonts.set(qn("w:ascii"), "Consolas")
    code._element.rPr.rFonts.set(qn("w:hAnsi"), "Consolas")
    code.font.size = Pt(8.2)
    code.paragraph_format.left_indent = Inches(0.12); code.paragraph_format.right_indent = Inches(0.12)
    code.paragraph_format.space_before = Pt(3); code.paragraph_format.space_after = Pt(6)
    code.paragraph_format.line_spacing = 1.0
    callout = styles.add_style("Callout", 1)
    callout.font.name = "Calibri"
    callout._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    callout._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    callout.font.size = Pt(10.2)
    callout.paragraph_format.left_indent = Inches(0.12); callout.paragraph_format.right_indent = Inches(0.12)
    callout.paragraph_format.space_before = Pt(4); callout.paragraph_format.space_after = Pt(8)
    callout.paragraph_format.line_spacing = 1.15


def configure_section(section):
    section.page_width = Inches(8.5); section.page_height = Inches(11)
    section.top_margin = Inches(1); section.bottom_margin = Inches(1)
    section.left_margin = Inches(1); section.right_margin = Inches(1)
    section.header_distance = Inches(0.492); section.footer_distance = Inches(0.492)
    header = section.header; p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT; p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Application Monitoring  |  GitLab & Jenkins  |  End-to-End")
    set_run_font(r, size=9, bold=True, color=MUTED)
    set_para_border_bottom(p, color="D0D5DD", size=4, space=3)
    footer = section.footer; p = footer.paragraphs[0]
    p.paragraph_format.space_before = Pt(2); add_page_number(p)


def page_break(doc):
    doc.add_page_break()


doc = Document()
configure_styles(doc)
for section in doc.sections:
    configure_section(section)

# ---------------------------------------------------------------- Cover
for _ in range(5):
    doc.add_paragraph()
for text, size, bold, color, after, italic in [
    ("APPLICATION MONITORING RUNBOOK", 11, True, BLUE2, 18, False),
    ("GitLab & Jenkins — End-to-End", 28, True, BLUE, 8, False),
    ("Prometheus + Grafana monitoring on Red Hat Enterprise Linux 9", 14, False, BLUE2, 26, False),
    ("Companion to the Grafana Monitoring Platform installation runbook", 10.5, True, MUTED, 70, False),
    ("Target-server setup, scrape configuration, alerting, and dashboards", 10.5, False, MUTED, 6, True),
    ("Version 1.0  |  RHEL 9", 10, False, MUTED, 0, False),
]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); set_run_font(r, size=size, bold=bold, italic=italic, color=color)
    p.paragraph_format.space_after = Pt(after)

page_break(doc)

# ---------------------------------------------------------------- Purpose
add_heading(doc, "Purpose and scope", 1)
add_body(doc, "This runbook wires two servers we already run - a GitLab box used purely for git, and a Jenkins CI box - into the Prometheus, Grafana, and Alertmanager stack from the platform runbook. For each one it walks through what has to change on the server itself, the scrape config on the monitoring side, the alert rules, a dashboard, and how to prove it actually works.")

add_callout(doc, "Prerequisite", "None of this works until the monitoring server is already up: Prometheus, Grafana, Alertmanager, Node Exporter (platform runbook Section 5), and Blackbox Exporter (Section 14). We are not reinstalling any of that here - only adding the two targets and their scrape, alert, and dashboard config.", "note")

add_callout(doc, "Who does what", "Three different people touch this. The GitLab owners apply the gitlab.rb change, the Jenkins admins install the plugin, and you handle everything on the monitoring server. Each section says which is which, because you will be waiting on other teams for parts of it - plan the sequencing around that.", "warning")

add_heading(doc, "What is monitored", 2)
add_table(
    doc,
    ["Server", "Role", "Key signals"],
    [
        ("GitLab", "SCM (git hosting only)", "Gitaly git-RPC health, repo disk, component up/down, HTTPS+SSH reachability"),
        ("Jenkins", "CI automation server", "Build queue, executors, job results, JVM heap, JENKINS_HOME disk, HTTPS reachability"),
    ],
    [1600, 2600, 5160],
)
add_body(doc, "What we are leaving out: anything application-internal, GitLab's CI and registry (we do not use them), and deep Jenkins agent internals past what the controller already reports. Any of it is easy to add later if that changes.")

page_break(doc)

# ---------------------------------------------------------------- 1. Topology
add_heading(doc, "1. Placeholders and topology", 1)
add_heading(doc, "1.1 Replace these values", 2)
add_table(
    doc,
    ["Placeholder", "Meaning", "Example"],
    [
        ("<MON_IP>", "Monitoring server address", "10.10.10.11"),
        ("<GITLAB_IP>", "GitLab server address", "10.10.10.20"),
        ("<GITLAB_FQDN>", "GitLab URL host", "gitlab.example.com"),
        ("<GIT_DATA_MOUNT>", "Filesystem holding git repos", "/var/opt/gitlab"),
        ("<JENKINS_IP>", "Jenkins server address", "10.10.10.21"),
        ("<JENKINS_FQDN>", "Jenkins URL host", "jenkins.example.com"),
        ("<JENKINS_PORT>", "Jenkins HTTP port", "8080"),
        ("<JENKINS_HOME_MOUNT>", "Filesystem holding JENKINS_HOME", "/var"),
        ("<JENKINS_USER>", "Jenkins read-only monitoring user", "prometheus-ro"),
    ],
    [2500, 3860, 3000],
)

add_heading(doc, "1.2 Topology", 2)
add_code(doc, """
                     Monitoring server  (<MON_IP>)
        +-----------------------------------------------------+
        |  Prometheus :9090     Alertmanager :9093            |
        |  Grafana :3000        Blackbox Exporter :9115       |
        +----------------+--------------------+---------------+
             scrape /    |                    |   \\ scrape
            probe        |                    |    \\
          +--------------+                    +-----------------+
          v                                                    v
   GitLab server (<GITLAB_IP>)                 Jenkins server (<JENKINS_IP>)
     node_exporter    :9100                      node_exporter      :9100
     gitaly           :9236                      Jenkins + Prometheus plugin
     gitlab-exporter  :9168                      <JENKINS_PORT>/prometheus/
     workhorse/puma/sidekiq                      (JVM, queue, executors,
     postgres/redis exporters                     job results, health score)

   Blackbox probes: GitLab SSH:22 + HTTPS:443 ,  Jenkins HTTPS/HTTP login page
""")

add_heading(doc, "1.3 Endpoint and port matrix", 2)
add_table(
    doc,
    ["Server", "Endpoint", "Port / path", "Exposed to"],
    [
        ("GitLab", "node_exporter", "9100", "<MON_IP> only"),
        ("GitLab", "gitaly", "9236", "<MON_IP> only"),
        ("GitLab", "gitlab-exporter", "9168", "<MON_IP> only"),
        ("GitLab", "workhorse/puma/sidekiq/pg/redis", "9229/8083/8082/9187/9121", "<MON_IP> only"),
        ("Jenkins", "node_exporter", "9100", "<MON_IP> only"),
        ("Jenkins", "Prometheus plugin", "<JENKINS_PORT> /prometheus/", "<MON_IP> (or authenticated)"),
        ("Both", "Blackbox probe targets", "GitLab 22/443, Jenkins <JENKINS_PORT>/443", "from <MON_IP>"),
    ],
    [1400, 2900, 3060, 2000],
)

page_break(doc)

# ---------------------------------------------------------------- 2. Common
add_heading(doc, "2. Common building blocks (both servers)", 1)
add_heading(doc, "2.1 Node Exporter on each application server", 2)
add_body(doc, "Node Exporter gives you CPU, memory, and the one that actually causes outages - disk on the repo and JENKINS_HOME volumes. The install is the same as platform runbook Section 5. Skip it on GitLab: Omnibus already ships node_exporter, so you switch it on in gitlab.rb (Section 3) instead of installing anything.")
add_code(doc, """
cd /tmp
curl -fLO https://github.com/prometheus/node_exporter/releases/download/v1.12.1/\
node_exporter-1.12.1.linux-amd64.tar.gz

echo "b51d8a76aa2a9156a55d501aca6276fae09e262259a5e4e831d2c2222f084e63  \
node_exporter-1.12.1.linux-amd64.tar.gz" | sha256sum -c -

tar -xzf node_exporter-1.12.1.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin node_exporter
sudo install -m 0755 node_exporter-1.12.1.linux-amd64/node_exporter \
  /usr/local/bin/node_exporter

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
curl -fsS http://localhost:9100/metrics | head
""")
add_body(doc, "Restrict port 9100 to the monitoring server (skip on GitLab if node_exporter is exposed via gitlab.rb, which is covered in Section 3):")
add_code(doc, """
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" \
  source address="<MON_IP>/32" port protocol="tcp" port="9100" accept'
sudo firewall-cmd --reload
""")

add_heading(doc, "2.2 Blackbox front-door probes", 2)
add_body(doc, "Blackbox (platform runbook Section 14) checks the front door - the port developers actually hit - without caring what the internal metrics claim. A service can look healthy in its own metrics while the login page throws 502s; this is what catches that. Both sections below add probe jobs pointing at it, so there is nothing to set up here beyond confirming it runs:")
add_code(doc, """
sudo systemctl is-active blackbox_exporter
curl -fsS http://127.0.0.1:9115/-/healthy
""")

add_heading(doc, "2.3 Grafana preparation", 2)
add_body(doc, "In Grafana, check the Prometheus data source is there (platform runbook Section 8.4) and make two folders, GitLab and Jenkins, to keep the imported dashboards from piling up in one list. Everything points at Prometheus. Not the GitLab data-source plugin - that one talks to the GitLab API for merge-request and pipeline stats, which is a different job than health monitoring.")

page_break(doc)

# ---------------------------------------------------------------- 3. GitLab
add_heading(doc, "3. GitLab (SCM) - end to end", 1)
add_heading(doc, "3.1 What GitLab exposes", 2)
add_body(doc, "Omnibus already runs every exporter we need. They just listen on localhost, so the whole GitLab task is opening them up to the monitoring server. No installs, no new packages.")
add_table(
    doc,
    ["Exporter", "Port", "Signal", "Priority"],
    [
        ("node_exporter", "9100", "Host CPU/mem/disk (repo storage)", "Tier 1"),
        ("gitaly", "9236", "Git RPC latency/errors (git engine)", "Tier 1"),
        ("gitlab-exporter", "9168", "Rails/DB/ring health", "Tier 1"),
        ("workhorse", "9229", "HTTP git payloads, 5xx rates", "Tier 2"),
        ("puma", "8083", "Web/API request rates + errors", "Tier 2"),
        ("sidekiq", "8082", "Background jobs (mirroring, webhooks)", "Tier 2"),
        ("postgres_exporter", "9187", "Bundled PostgreSQL", "Tier 2"),
        ("redis_exporter", "9121", "Bundled Redis", "Tier 2"),
    ],
    [2300, 900, 4360, 1800],
)

add_heading(doc, "3.2 Change request for the GitLab owners", 2)
add_body(doc, "Provide this to the GitLab platform team. Edit /etc/gitlab/gitlab.rb:")
add_code(doc, """
# Allow the monitoring server to read health/metrics endpoints
gitlab_rails['monitoring_whitelist'] = ['127.0.0.0/8', '<MON_IP>/32']

# Tier 1: host + git engine + rails health
node_exporter['listen_address']   = '<GITLAB_IP>:9100'
gitlab_exporter['listen_address'] = '<GITLAB_IP>'
gitlab_exporter['listen_port']    = '9168'
gitaly['configuration'] = { prometheus_listen_addr: '<GITLAB_IP>:9236' }
# Older GitLab: gitaly['prometheus_listen_addr'] = '<GITLAB_IP>:9236'

# Tier 2: supporting services
gitlab_workhorse['prometheus_listen_addr'] = '<GITLAB_IP>:9229'
puma['exporter_enabled'] = true
puma['exporter_address'] = '<GITLAB_IP>'
puma['exporter_port']    = 8083
sidekiq['metrics_enabled'] = true
sidekiq['listen_address']  = '<GITLAB_IP>'
sidekiq['listen_port']     = 8082
postgres_exporter['listen_address'] = '<GITLAB_IP>:9187'
redis_exporter['listen_address']    = '<GITLAB_IP>:9121'
""")
add_body(doc, "Apply, then restrict the ports to the monitoring server only, and report the repo mount:")
add_code(doc, """
sudo gitlab-ctl reconfigure

for p in 9100 9236 9168 9229 8083 8082 9187 9121; do
  sudo firewall-cmd --permanent --add-rich-rule="rule family=\\"ipv4\\" \
    source address=\\"<MON_IP>/32\\" port protocol=\\"tcp\\" port=\\"$p\\" accept"
done
sudo firewall-cmd --reload
df -h /var/opt/gitlab/git-data
""")
add_callout(doc, "Security", "Binding to <GITLAB_IP> and the firewall rule together keep these ports internal and reachable only from <MON_IP>. Do not bind them to 0.0.0.0 or open them to the world - the exporters expose a lot about the box and have no auth of their own.", "warning")

add_heading(doc, "3.3 Prometheus scrape jobs (monitoring server)", 2)
add_body(doc, "Append under scrape_configs: in /etc/prometheus/prometheus.yml. Start with Tier 1; add Tier 2 once exposed.")
add_code(doc, """
  - job_name: gitlab-node
    static_configs: [ { targets: ['<GITLAB_IP>:9100'], labels: { service: gitlab, role: host } } ]
  - job_name: gitlab-gitaly
    static_configs: [ { targets: ['<GITLAB_IP>:9236'], labels: { service: gitlab, role: gitaly } } ]
  - job_name: gitlab-exporter
    static_configs: [ { targets: ['<GITLAB_IP>:9168'], labels: { service: gitlab, role: rails } } ]
  - job_name: gitlab-workhorse
    static_configs: [ { targets: ['<GITLAB_IP>:9229'], labels: { service: gitlab, role: workhorse } } ]
  - job_name: gitlab-puma
    static_configs: [ { targets: ['<GITLAB_IP>:8083'], labels: { service: gitlab, role: puma } } ]
  - job_name: gitlab-sidekiq
    static_configs: [ { targets: ['<GITLAB_IP>:8082'], labels: { service: gitlab, role: sidekiq } } ]
  - job_name: gitlab-postgres
    static_configs: [ { targets: ['<GITLAB_IP>:9187'], labels: { service: gitlab, role: postgres } } ]
  - job_name: gitlab-redis
    static_configs: [ { targets: ['<GITLAB_IP>:9121'], labels: { service: gitlab, role: redis } } ]
""")

add_heading(doc, "3.4 Front-door probes (blackbox)", 2)
add_code(doc, """
  - job_name: gitlab-blackbox-ssh
    metrics_path: /probe
    params: { module: [tcp_connect] }
    static_configs: [ { targets: ['<GITLAB_IP>:22'] } ]
    relabel_configs:
      - { source_labels: [__address__], target_label: __param_target }
      - { source_labels: [__param_target], target_label: instance }
      - { target_label: __address__, replacement: 127.0.0.1:9115 }
  - job_name: gitlab-blackbox-https
    metrics_path: /probe
    params: { module: [http_2xx] }
    static_configs: [ { targets: ['https://<GITLAB_FQDN>/-/readiness'] } ]
    relabel_configs:
      - { source_labels: [__address__], target_label: __param_target }
      - { source_labels: [__param_target], target_label: instance }
      - { target_label: __address__, replacement: 127.0.0.1:9115 }
""")

add_heading(doc, "3.5 Alert rules", 2)
add_callout(doc, "Verify metric names", "Metric names vary by GitLab version. After scraping starts, confirm each metric exists in the target's /metrics before trusting the rule.", "warning")
add_body(doc, "Create /etc/prometheus/rules/gitlab.yml:")
add_code(doc, """
groups:
  - name: gitlab-scm
    rules:
      - alert: GitLabComponentDown
        expr: up{service="gitlab"} == 0
        for: 5m
        labels: { severity: critical }
        annotations: { summary: "GitLab component down: {{ $labels.job }} ({{ $labels.instance }})" }
      - alert: GitLabRepoDiskLow
        expr: 100 * node_filesystem_avail_bytes{service="gitlab",mountpoint="<GIT_DATA_MOUNT>"}
              / node_filesystem_size_bytes{service="gitlab",mountpoint="<GIT_DATA_MOUNT>"} < 15
        for: 15m
        labels: { severity: critical }
        annotations: { summary: "GitLab repo disk <15% free on {{ $labels.instance }}" }
      - alert: GitalyErrors
        expr: sum by (grpc_method) (rate(grpc_server_handled_total{job="gitlab-gitaly",grpc_code!="OK"}[5m])) > 0
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "Gitaly errors on {{ $labels.grpc_method }} (clone/push may fail)" }
      - alert: GitalyHighLatency
        expr: histogram_quantile(0.99, sum by (le) (rate(grpc_server_handling_seconds_bucket{job="gitlab-gitaly"}[5m]))) > 1
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "Gitaly p99 git RPC latency > 1s" }
      - alert: GitLabUnreachable
        expr: probe_success{job=~"gitlab-blackbox.*"} == 0
        for: 3m
        labels: { severity: critical }
        annotations: { summary: "GitLab front door down: {{ $labels.instance }}" }
""")

add_heading(doc, "3.6 Dashboards and key queries", 2)
add_bullet(doc, "Git RPC rate: sum(rate(grpc_server_handled_total{job=\"gitlab-gitaly\"}[5m])) by (grpc_method)")
add_bullet(doc, "Git RPC errors: sum(rate(grpc_server_handled_total{job=\"gitlab-gitaly\",grpc_code!=\"OK\"}[5m]))")
add_bullet(doc, "Component up/down: up{service=\"gitlab\"}")
add_bullet(doc, "Repo disk free %: 100 * node_filesystem_avail_bytes{service=\"gitlab\",mountpoint=\"<GIT_DATA_MOUNT>\"} / node_filesystem_size_bytes{...}")
add_bullet(doc, "Front-door reachability: probe_success{job=~\"gitlab-blackbox.*\"}")
add_body(doc, "Import GitLab's official dashboards from grafana.com (search 'GitLab Omnibus' / 'Gitaly') into the GitLab folder, then set the data source to Prometheus.")

add_heading(doc, "3.7 Validation", 2)
add_code(doc, """
sudo promtool check config /etc/prometheus/prometheus.yml
sudo promtool check rules /etc/prometheus/rules/gitlab.yml
sudo systemctl reload-or-restart prometheus
curl -s 'http://127.0.0.1:9090/api/v1/query?query=up{service="gitlab"}'
""")

page_break(doc)

# ---------------------------------------------------------------- 4. Jenkins
add_heading(doc, "4. Jenkins (CI) - end to end", 1)
add_heading(doc, "4.1 What Jenkins exposes", 2)
add_body(doc, "Jenkins is a Java app, so the metrics come from a couple of different places. The host gives you Node Exporter like anything else. The Jenkins Prometheus plugin exposes the CI side - queue, executors, job results, health - and the JVM numbers ride along on the same endpoint. The difference from GitLab: none of it exists until you install that plugin and turn the endpoint on.")
add_table(
    doc,
    ["Source", "Endpoint", "Signal"],
    [
        ("Node Exporter", "9100", "Host CPU/mem/disk (JENKINS_HOME volume)"),
        ("Prometheus plugin", "<JENKINS_PORT>/prometheus/", "Queue, executors, node status, job results, health score"),
        ("JVM (via plugin)", "same endpoint", "Heap usage, GC, thread count"),
        ("Blackbox", "login page", "HTTPS/HTTP reachability from the outside"),
    ],
    [2100, 2800, 4460],
)

add_heading(doc, "4.2 Host metrics (Jenkins admin / host owner)", 2)
add_body(doc, "Install Node Exporter on the Jenkins host exactly as in Section 2.1, then add the firewall rule for port 9100 from <MON_IP>. Confirm which filesystem holds JENKINS_HOME so the disk alert targets it:")
add_code(doc, """
df -h /var/lib/jenkins
""")

add_heading(doc, "4.3 Install the Prometheus metrics plugin (Jenkins admin)", 2)
add_body(doc, "Option A - Jenkins UI (simplest):")
for n, t in enumerate([
    "Sign in to Jenkins as an administrator.",
    "Manage Jenkins -> Plugins -> Available plugins.",
    "Search for 'Prometheus metrics' and select it.",
    "Install, and check 'Restart Jenkins when installation is complete and no jobs are running'.",
], start=1):
    add_number(doc, t, n)
add_body(doc, "Option B - command line (for reproducible/offline installs on the Jenkins host):")
add_code(doc, """
# Using the Plugin Installation Manager tool (bundled with modern Jenkins images):
sudo jenkins-plugin-cli --plugins prometheus

# Or via the Jenkins CLI against a running controller:
java -jar jenkins-cli.jar -s http://<JENKINS_IP>:<JENKINS_PORT>/ \
  -auth <admin_user>:<admin_api_token> install-plugin prometheus -restart
""")

add_heading(doc, "4.4 Configure the plugin (Jenkins admin)", 2)
add_body(doc, "Manage Jenkins -> System -> scroll to the 'Prometheus' section and set:")
add_bullet(doc, "Path: prometheus  (the endpoint becomes <JENKINS_URL>/prometheus/).")
add_bullet(doc, "Collecting metrics period (seconds): 120  (how often Jenkins refreshes the exposed values).")
add_bullet(doc, "Enable 'Count successful/failed/unstable builds' and per-job build metrics as needed.")
add_bullet(doc, "'Use authenticated endpoint': see Section 4.5 - leave unchecked only if you restrict access by network/firewall.")
add_body(doc, "Save. Verify the endpoint returns Prometheus text (from the Jenkins host or an allowed source):")
add_code(doc, """
curl -fsS http://<JENKINS_IP>:<JENKINS_PORT>/prometheus/ | head
""")
add_callout(doc, "Trailing slash", "The plugin serves metrics at /prometheus/ (with the trailing slash). Prometheus must scrape metrics_path: /prometheus/ or the scrape returns 404.", "note")

add_heading(doc, "4.5 Secure the metrics endpoint (choose one)", 2)
add_body(doc, "The /prometheus/ endpoint should not be world-readable. Pick the option that matches your Jenkins security model.")
add_body(doc, "Option 1 - Network restriction (simplest). Leave the endpoint unauthenticated but allow only the monitoring server at the firewall (and/or reverse proxy):")
add_code(doc, """
# On the Jenkins host:
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" \
  source address="<MON_IP>/32" port protocol="tcp" port="<JENKINS_PORT>" accept'
sudo firewall-cmd --reload
""")
add_body(doc, "Option 2 - Authenticated scrape (preferred when Jenkins is behind a shared proxy). Create a dedicated read-only Jenkins user with an API token, then have Prometheus authenticate:")
for n, t in enumerate([
    "In Jenkins, create a user (for example <JENKINS_USER>) with only Overall/Read permission.",
    "As that user: profile -> Security -> Add new API token -> copy the token.",
    "Enable 'Use authenticated endpoint' in the Prometheus plugin config.",
    "Store the token on the monitoring server for Prometheus (Section 4.6).",
], start=1):
    add_number(doc, t, n)

add_heading(doc, "4.6 Prometheus scrape job (monitoring server)", 2)
add_body(doc, "If using Option 1 (network-restricted, unauthenticated), add:")
add_code(doc, """
  - job_name: jenkins
    metrics_path: /prometheus/
    scheme: http
    static_configs:
      - targets: ['<JENKINS_IP>:<JENKINS_PORT>']
        labels: { service: jenkins, role: controller }
""")
add_body(doc, "If using Option 2 (authenticated), store the token and reference it. Jenkins API tokens use HTTP Basic auth (username + token as password):")
add_code(doc, """
sudo install -d -o prometheus -g prometheus -m 0750 /etc/prometheus/secrets
printf '%s' '<JENKINS_API_TOKEN>' | sudo tee /etc/prometheus/secrets/jenkins_token >/dev/null
sudo chown prometheus:prometheus /etc/prometheus/secrets/jenkins_token
sudo chmod 0640 /etc/prometheus/secrets/jenkins_token
""")
add_code(doc, """
  - job_name: jenkins
    metrics_path: /prometheus/
    scheme: http            # use https if Jenkins is behind TLS (then set the LB/proxy port)
    basic_auth:
      username: <JENKINS_USER>
      password_file: /etc/prometheus/secrets/jenkins_token
    static_configs:
      - targets: ['<JENKINS_IP>:<JENKINS_PORT>']
        labels: { service: jenkins, role: controller }
""")

add_heading(doc, "4.7 Front-door probe (blackbox)", 2)
add_body(doc, "Confirm the Jenkins login page answers from the outside:")
add_code(doc, """
  - job_name: jenkins-blackbox
    metrics_path: /probe
    params: { module: [http_2xx] }
    static_configs: [ { targets: ['http://<JENKINS_IP>:<JENKINS_PORT>/login'] } ]
    relabel_configs:
      - { source_labels: [__address__], target_label: __param_target }
      - { source_labels: [__param_target], target_label: instance }
      - { target_label: __address__, replacement: 127.0.0.1:9115 }
""")

add_heading(doc, "4.8 Alert rules", 2)
add_callout(doc, "Verify metric names", "Jenkins Prometheus-plugin metric names vary by plugin version. After scraping starts, open <JENKINS_URL>/prometheus/ and confirm each metric name below exists; adjust if the plugin uses a different name.", "warning")
add_body(doc, "Create /etc/prometheus/rules/jenkins.yml:")
add_code(doc, """
groups:
  - name: jenkins
    rules:
      - alert: JenkinsDown
        expr: up{job="jenkins"} == 0
        for: 5m
        labels: { severity: critical }
        annotations: { summary: "Jenkins scrape target down ({{ $labels.instance }})" }
      - alert: JenkinsUnreachable
        expr: probe_success{job="jenkins-blackbox"} == 0
        for: 3m
        labels: { severity: critical }
        annotations: { summary: "Jenkins login page unreachable" }
      - alert: JenkinsHomeDiskLow
        expr: 100 * node_filesystem_avail_bytes{service="jenkins",mountpoint="<JENKINS_HOME_MOUNT>"}
              / node_filesystem_size_bytes{service="jenkins",mountpoint="<JENKINS_HOME_MOUNT>"} < 15
        for: 15m
        labels: { severity: critical }
        annotations: { summary: "JENKINS_HOME disk <15% free on {{ $labels.instance }}" }
      - alert: JenkinsQueueBacklog
        expr: jenkins_queue_size_value > 20
        for: 15m
        labels: { severity: warning }
        annotations: { summary: "Jenkins build queue > 20 for 15m (executors saturated?)" }
      - alert: JenkinsAllExecutorsBusy
        expr: (jenkins_executor_count_value - jenkins_executor_in_use_value) < 1
        for: 30m
        labels: { severity: warning }
        annotations: { summary: "No free Jenkins executors for 30m" }
      - alert: JenkinsHealthDegraded
        expr: jenkins_health_check_score < 1
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "Jenkins health-check score below 1" }
      - alert: JenkinsJVMHeapHigh
        expr: vm_memory_heap_usage > 0.9
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "Jenkins JVM heap >90% (verify metric name)" }
""")

add_heading(doc, "4.9 Dashboards and key queries", 2)
add_bullet(doc, "Build queue length: jenkins_queue_size_value")
add_bullet(doc, "Executor utilization: jenkins_executor_in_use_value / jenkins_executor_count_value")
add_bullet(doc, "Health score: jenkins_health_check_score")
add_bullet(doc, "JENKINS_HOME disk free %: 100 * node_filesystem_avail_bytes{service=\"jenkins\",mountpoint=\"<JENKINS_HOME_MOUNT>\"} / node_filesystem_size_bytes{...}")
add_bullet(doc, "JVM heap usage: vm_memory_heap_usage  (verify name against your plugin)")
add_bullet(doc, "Reachability: probe_success{job=\"jenkins-blackbox\"}")
add_body(doc, "Import a Jenkins Prometheus dashboard from grafana.com (search 'Jenkins Prometheus') into the Jenkins folder and set its data source to Prometheus. Confirm each panel resolves against your metric names.")

add_heading(doc, "4.10 Validation", 2)
add_code(doc, """
sudo promtool check config /etc/prometheus/prometheus.yml
sudo promtool check rules /etc/prometheus/rules/jenkins.yml
sudo systemctl reload-or-restart prometheus
curl -s 'http://127.0.0.1:9090/api/v1/query?query=up{job="jenkins"}'
""")

page_break(doc)

# ---------------------------------------------------------------- 5. Acceptance
add_heading(doc, "5. Combined acceptance checklist", 1)
for item in [
    "GitLab owners applied the gitlab.rb change; gitlab-ctl reconfigure succeeded.",
    "All gitlab-* targets show UP in Prometheus.",
    "GitLab blackbox SSH and HTTPS probes report probe_success == 1.",
    "GitLab repo-disk alert points at the confirmed <GIT_DATA_MOUNT>.",
    "Jenkins Node Exporter installed; port 9100 restricted to <MON_IP>.",
    "Jenkins Prometheus plugin installed, configured, and /prometheus/ returns metrics.",
    "Jenkins endpoint secured (network-restricted or authenticated) - not world-readable.",
    "Jenkins scrape target shows UP; jenkins_queue_size_value and executor metrics resolve.",
    "Jenkins blackbox login probe reports probe_success == 1.",
    "JENKINS_HOME disk alert points at the confirmed <JENKINS_HOME_MOUNT>.",
    "One alert per server tested end-to-end (stop target -> alert fires -> notification).",
    "Grafana GitLab and Jenkins folders each render component health, disk, and reachability.",
]:
    add_bullet(doc, "\u2610 " + item)

page_break(doc)

# ---------------------------------------------------------------- Appendices
add_heading(doc, "Appendix A - Troubleshooting", 1)
add_table(
    doc,
    ["Symptom", "Checks"],
    [
        ("GitLab target DOWN", "Test the exporter port from the monitoring server; confirm gitlab.rb listen_address and firewall; check monitoring_whitelist."),
        ("Gitaly metrics missing", "Confirm gitaly prometheus_listen_addr syntax for the GitLab version; reconfigure; curl <GITLAB_IP>:9236/metrics."),
        ("Jenkins scrape 404", "metrics_path must be /prometheus/ (trailing slash); confirm the plugin Path setting."),
        ("Jenkins scrape 403", "Endpoint requires auth; use Option 2 (basic_auth with API token) or enable network-restricted access."),
        ("Jenkins metrics empty", "Increase build activity or lower the collecting period; confirm the plugin is enabled after restart."),
        ("Disk alert never fires / wrong disk", "Confirm the mountpoint label matches df output on the target; adjust <..._MOUNT>."),
        ("Blackbox probe fails", "Confirm blackbox_exporter is running on 127.0.0.1:9115 and the target scheme/port are correct."),
    ],
    [2600, 6760],
)

add_heading(doc, "Appendix B - Endpoint quick reference", 1)
add_table(
    doc,
    ["Job", "Target", "Path", "Auth"],
    [
        ("gitlab-node", "<GITLAB_IP>:9100", "/metrics", "none (firewall)"),
        ("gitlab-gitaly", "<GITLAB_IP>:9236", "/metrics", "none (firewall)"),
        ("gitlab-exporter", "<GITLAB_IP>:9168", "/metrics", "none (firewall)"),
        ("gitlab-blackbox-*", "SSH:22 / HTTPS:443", "/probe", "via blackbox"),
        ("jenkins", "<JENKINS_IP>:<JENKINS_PORT>", "/prometheus/", "firewall or basic_auth"),
        ("jenkins-blackbox", "<JENKINS_IP>:<JENKINS_PORT>/login", "/probe", "via blackbox"),
    ],
    [2200, 3200, 1960, 2000],
)

add_callout(doc, "Version note", "Node Exporter 1.12.1 and Blackbox Exporter 0.28.0 are pinned in the platform runbook. The Jenkins Prometheus plugin installs from the Jenkins update center - record the installed plugin version in change control. Revalidate all metric names against live /metrics output before relying on alerts.", "note")

doc.core_properties.title = "Application Monitoring - GitLab and Jenkins End-to-End"
doc.core_properties.subject = "Prometheus/Grafana monitoring for GitLab and Jenkins on RHEL 9"
doc.core_properties.author = "Platform Engineering"
doc.core_properties.keywords = "GitLab, Jenkins, Prometheus, Grafana, Node Exporter, Blackbox, monitoring"

settings = doc.settings._element
uf = settings.find(qn("w:updateFields"))
if uf is None:
    uf = OxmlElement("w:updateFields"); settings.append(uf)
uf.set(qn("w:val"), "true")

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
