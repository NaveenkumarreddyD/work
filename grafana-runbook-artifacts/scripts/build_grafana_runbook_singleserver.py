from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


OUT = Path("/Users/naveendubba/Documents/Ibm mas and manage/"
           "Grafana_Installation_RHEL9_SingleServer.docx")

BLUE = "1F4E78"
BLUE2 = "2E74B5"
DARK = "1F2937"
MUTED = "667085"
LIGHT_BLUE = "E8EEF5"
CODE_FILL = "F5F7FA"
CAUTION_FILL = "FFF4CE"
RISK_FILL = "FDECEC"
GREEN_FILL = "EAF5EA"
TABLE_WIDTH = 9360
TABLE_INDENT = 120


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths):
    assert sum(widths) == TABLE_WIDTH
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(TABLE_WIDTH))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(TABLE_INDENT))
    tbl_ind.set(qn("w:type"), "dxa")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths[idx]))
            tc_w.set(qn("w:type"), "dxa")
            cell.width = Inches(widths[idx] / 1440)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_run_font(run, name="Calibri", size=11, bold=None, italic=None, color=DARK):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_para_border_bottom(paragraph, color=BLUE, size=10, space=4):
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), str(space))
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)


def shade_paragraph(paragraph, fill):
    p_pr = paragraph._p.get_or_add_pPr()
    shd = p_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        p_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_text(cell, text, bold=False, color=DARK, size=9.5, align=WD_ALIGN_PARAGRAPH.LEFT):
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.1
    r = p.add_run(text)
    set_run_font(r, size=size, bold=bold, color=color)


def add_table(doc, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    set_table_geometry(table, widths)
    header = table.rows[0]
    set_repeat_table_header(header)
    for idx, text in enumerate(headers):
        set_cell_shading(header.cells[idx], LIGHT_BLUE)
        set_cell_text(header.cells[idx], text, bold=True, color=BLUE, size=9.2)
    for row_data in rows:
        row = table.add_row()
        for idx, text in enumerate(row_data):
            set_cell_text(row.cells[idx], str(text), size=9.2)
    after = doc.add_paragraph()
    after.paragraph_format.space_after = Pt(2)
    return table


def add_code(doc, text):
    p = doc.add_paragraph(style="Code Block")
    p.paragraph_format.keep_together = True
    shade_paragraph(p, CODE_FILL)
    r = p.add_run(text.strip("\n"))
    set_run_font(r, name="Consolas", size=8.2, color="202124")
    return p


def add_callout(doc, label, text, kind="note"):
    fill = {"note": LIGHT_BLUE, "warning": CAUTION_FILL, "risk": RISK_FILL, "success": GREEN_FILL}[kind]
    p = doc.add_paragraph(style="Callout")
    shade_paragraph(p, fill)
    r = p.add_run(f"{label}: ")
    set_run_font(r, size=10.2, bold=True, color=BLUE if kind != "risk" else "9B1C1C")
    r = p.add_run(text)
    set_run_font(r, size=10.2, color=DARK)
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.paragraph_format.left_indent = Inches(0.375 + level * 0.25)
    p.paragraph_format.first_line_indent = Inches(-0.188)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(text)
    set_run_font(r, size=10.5)
    return p


def add_number(doc, text, number):
    p = doc.add_paragraph(style="Normal")
    p.paragraph_format.left_indent = Inches(0.375)
    p.paragraph_format.first_line_indent = Inches(-0.188)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(f"{number}.  {text}")
    set_run_font(r, size=10.5)
    return p


def add_body(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="Normal")
    if bold_lead and text.startswith(bold_lead):
        r = p.add_run(bold_lead)
        set_run_font(r, bold=True)
        r = p.add_run(text[len(bold_lead):])
        set_run_font(r)
    else:
        r = p.add_run(text)
        set_run_font(r)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(text, style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    return p


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    set_run_font(run, size=9, color=MUTED)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)


def configure_styles(doc):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(DARK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    tokens = {
        "Heading 1": (16, BLUE2, 18, 10),
        "Heading 2": (13, BLUE2, 14, 7),
        "Heading 3": (12, BLUE, 10, 5),
    }
    for name, (size, color, before, after) in tokens.items():
        style = styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    code = styles.add_style("Code Block", 1)
    code.font.name = "Consolas"
    code._element.rPr.rFonts.set(qn("w:ascii"), "Consolas")
    code._element.rPr.rFonts.set(qn("w:hAnsi"), "Consolas")
    code.font.size = Pt(8.2)
    code.paragraph_format.left_indent = Inches(0.12)
    code.paragraph_format.right_indent = Inches(0.12)
    code.paragraph_format.space_before = Pt(3)
    code.paragraph_format.space_after = Pt(6)
    code.paragraph_format.line_spacing = 1.0

    callout = styles.add_style("Callout", 1)
    callout.font.name = "Calibri"
    callout._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    callout._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    callout.font.size = Pt(10.2)
    callout.paragraph_format.left_indent = Inches(0.12)
    callout.paragraph_format.right_indent = Inches(0.12)
    callout.paragraph_format.space_before = Pt(4)
    callout.paragraph_format.space_after = Pt(8)
    callout.paragraph_format.line_spacing = 1.15


def configure_section(section):
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Operations Runbook  |  Grafana Monitoring Platform  |  Production")
    set_run_font(r, size=9, bold=True, color=MUTED)
    set_para_border_bottom(p, color="D0D5DD", size=4, space=3)

    footer = section.footer
    p = footer.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    add_page_number(p)


def page_break(doc):
    doc.add_page_break()


doc = Document()
configure_styles(doc)
for section in doc.sections:
    configure_section(section)

# ---------------------------------------------------------------- Cover
for _ in range(5):
    doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("PRODUCTION INSTALLATION RUNBOOK")
set_run_font(r, size=11, bold=True, color=BLUE2)
p.paragraph_format.space_after = Pt(18)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Grafana Monitoring Platform")
set_run_font(r, size=30, bold=True, color=BLUE)
p.paragraph_format.space_after = Pt(8)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Production Deployment on Red Hat Enterprise Linux 9")
set_run_font(r, size=15, color=BLUE2)
p.paragraph_format.space_after = Pt(28)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Grafana OSS • PostgreSQL 16 • Prometheus LTS • Alertmanager • Node Exporter")
set_run_font(r, size=10.5, bold=True, color=MUTED)
p.paragraph_format.space_after = Pt(72)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Prepared for on-premises DevOps application monitoring")
set_run_font(r, size=10.5, italic=True, color=MUTED)
p.paragraph_format.space_after = Pt(6)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Version 1.0  |  23 July 2026")
set_run_font(r, size=10, color=MUTED)

page_break(doc)

# ---------------------------------------------------- Purpose & decision
add_heading(doc, "Document purpose and deployment decision", 1)
add_body(doc, "This runbook provides a complete production build, configuration, validation, backup, and recovery procedure for a Grafana monitoring platform on RHEL 9. It covers Grafana OSS, PostgreSQL, Prometheus, Alertmanager, and Node Exporter, co-located on one monitoring server that observes the organization's application and Linux servers.")

add_callout(
    doc,
    "Recovery model",
    "This design has no automatic failover. If the monitoring server fails, monitoring, dashboards, and alerting are unavailable until the server is restored or rebuilt from backup. Backup integrity and a rehearsed restore procedure are therefore the primary recovery controls and must meet the agreed recovery-time and recovery-point objectives.",
    "warning",
)

add_callout(
    doc,
    "External DNS and load balancing",
    "User-facing DNS, TLS termination, and any load balancer are provided separately by the organization's network and platform teams and are requested through the normal change process. This runbook exposes Grafana on HTTP port 3000 behind that organization-managed entry point; it does not install NGINX or a local reverse proxy.",
    "note",
)

add_table(
    doc,
    ["Item", "Selected design"],
    [
        ("Operating system", "Red Hat Enterprise Linux 9, x86_64"),
        ("Grafana", "Grafana OSS, single instance on port 3000"),
        ("Grafana database", "PostgreSQL 16, single local instance (loopback)"),
        ("Metrics", "Prometheus 3.13.1 LTS, single instance"),
        ("Notifications", "Alertmanager 0.33.1, single instance (no clustering)"),
        ("Host metrics", "Node Exporter 1.12.1 on this server and each application server"),
        ("User access", "HTTPS via organization-managed DNS and load balancer to Grafana :3000"),
        ("Recovery model", "Restore from backup; no automatic failover"),
    ],
    [2500, 6860],
)

add_heading(doc, "Scope", 2)
for item in [
    "Installation and service configuration of all components on one monitoring server.",
    "PostgreSQL 16 initialization and use as the Grafana backend database.",
    "Prometheus collection, retention controls, and alert rules.",
    "Alertmanager single-node notification routing and integration placeholders.",
    "Grafana installation, Prometheus data-source provisioning, and access hardening.",
    "Integration patterns for GitLab, Jenkins, SonarQube, Nexus, and Linux servers.",
    "Firewall, SELinux, authentication, backup, patching, monitoring, and acceptance tests.",
]:
    add_bullet(doc, item)

add_heading(doc, "Out of scope", 2)
for item in [
    "Host or component high availability, replication, and automatic failover.",
    "User-facing DNS, TLS certificate issuance, and load-balancer configuration (organization supplied).",
    "A long-term deduplicating metrics store such as Thanos or Grafana Mimir.",
    "Organization-specific SSO, SMTP, Teams, ServiceNow, or PagerDuty credentials.",
    "Application changes that require approval from GitLab, Jenkins, SonarQube, or Nexus owners.",
]:
    add_bullet(doc, item)

add_heading(doc, "Source-controlled artifacts", 2)
add_body(doc, "Store the following files in an approved private configuration repository. Never commit passwords, API tokens, private keys, or unencrypted database credentials.")
for item in [
    "/etc/prometheus/prometheus.yml and /etc/prometheus/rules/*.yml",
    "/etc/alertmanager/alertmanager.yml with secrets supplied at deployment time",
    "/etc/grafana/grafana.ini and /etc/grafana/provisioning/",
    "Systemd unit files and the tested recovery procedure",
]:
    add_bullet(doc, item)

page_break(doc)

# ------------------------------------------------- 1. Architecture
add_heading(doc, "1. Architecture and naming", 1)
add_heading(doc, "1.1 Component placement", 2)
add_table(
    doc,
    ["Component", "Host", "Listen address", "Notes"],
    [
        ("PostgreSQL 16", "Monitoring server", "127.0.0.1:5432", "Grafana backend database, loopback only"),
        ("Grafana OSS", "Monitoring server", "0.0.0.0:3000", "Reached by the organization load balancer"),
        ("Prometheus LTS", "Monitoring server", "127.0.0.1:9090", "Scrapes all targets, evaluates rules"),
        ("Alertmanager", "Monitoring server", "127.0.0.1:9093", "Single node, clustering disabled"),
        ("Node Exporter", "Monitoring + app servers", "0.0.0.0:9100", "Host metrics, restricted by firewall"),
    ],
    [2100, 2000, 2000, 3260],
)

add_heading(doc, "1.2 Replace these values", 2)
add_callout(doc, "Before execution", "Replace every angle-bracket value in this runbook. Do not paste a command containing <PLACEHOLDER> into a production shell.", "risk")
add_table(
    doc,
    ["Placeholder", "Example", "Purpose"],
    [
        ("<MON_FQDN>", "mon01.example.com", "Monitoring server hostname"),
        ("<MON_IP>", "10.10.10.11", "Monitoring server address"),
        ("<GRAFANA_FQDN>", "grafana.example.com", "User-facing Grafana DNS (org LB)"),
        ("<APPROVED_CIDR>", "10.20.0.0/16", "Authorized user / load-balancer network"),
        ("<PROM_RETENTION_SIZE>", "40GB", "~80% of the 50 GB /u01 Prometheus mount"),
        ("<SMTP_OR_WEBHOOK>", "Organization supplied", "Alert delivery destination"),
        ("<BACKUP_PATH>", "/backup/monitoring", "Approved protected backup destination"),
    ],
    [2200, 2600, 4560],
)

add_heading(doc, "1.3 Data flow", 2)
add_code(doc, """
Users --HTTPS/443--> Organization DNS + Load Balancer (TLS termination)
                          |
                          +--HTTP/3000--> Grafana (single host)
                                              |
                                              +--> Prometheus/9090 (loopback)
                                              +--> PostgreSQL/5432 (loopback)

Prometheus --> Node Exporter/9100 (local host and application servers)
Prometheus --> application metrics endpoints
Prometheus --> Alertmanager/9093 (loopback) --> Approved notification channel
""")

add_heading(doc, "1.4 Availability behavior", 2)
add_table(
    doc,
    ["Failure", "Expected behavior", "Required action"],
    [
        ("A single component (Prometheus, Alertmanager, Grafana)", "systemd restarts the failed unit automatically.", "Investigate logs; confirm the service returned."),
        ("Node Exporter on an application server", "That host's metrics gap; TargetDown alert fires.", "Repair the exporter or host."),
        ("The monitoring server", "All monitoring, dashboards, and alerting are unavailable.", "Restore the host, then restore PostgreSQL and configuration from backup."),
        ("Corrupted or lost Grafana database", "Dashboards, users, and data sources are lost.", "Restore the latest PostgreSQL backup and restart Grafana."),
    ],
    [2300, 4000, 3060],
)
add_callout(doc, "Recovery depends on backups", "Because recovery relies on rebuilding from backup rather than automatic failover, backup integrity and a rehearsed restore procedure are the primary recovery controls. Validate backups and test restores on a schedule (Section 11).", "warning")

page_break(doc)

# ------------------------------------------------- 2. Prerequisites
add_heading(doc, "2. Prerequisites and security approvals", 1)
add_heading(doc, "2.1 Server minimums", 2)
add_body(doc, "Final capacity must be calculated from target count, active time-series count, scrape interval, retention, dashboard concurrency, and alert volume. Because all components share one host, size generously. The following is a starting point, not an automatic sizing approval.")
add_table(
    doc,
    ["Resource", "Starting point", "Notes"],
    [
        ("CPU", "4-8 vCPU", "Prometheus query and ingestion plus Grafana and PostgreSQL share the host."),
        ("Memory", "16 GB", "Increase for high series cardinality or concurrent dashboards."),
        ("OS disk", "40 GB", "Separate from Prometheus and PostgreSQL data where possible."),
        ("Prometheus data", "50 GB on /u01 (provisioned)", "Dedicated local mount. Cap retention to ~40 GB; see 2.1.2."),
        ("PostgreSQL data", "Default location, low volume", "Grafana metadata only; kept on the OS/default filesystem."),
        ("Backup volume", "Sized to retention policy", "Separate/off-host protected location strongly preferred."),
    ],
    [1800, 2450, 5110],
)

add_heading(doc, "2.1.1 Per-component resource share", 2)
add_body(doc, "On a single host the components share CPU and memory, so size the server to the sum, not to any one component. Prometheus dominates memory and disk; the others are comparatively light.")
add_table(
    doc,
    ["Component", "Memory (typical)", "Disk", "Notes"],
    [
        ("Prometheus", "4-8 GB", "50 GB /u01", "Scales ~linearly with active series (~7.5 KiB/series head, plus query and compaction overhead)."),
        ("Grafana OSS", "2-4 GB", "10-20 GB SSD", "Grafana's own 'small/medium' tier; grows with concurrent users and plugins."),
        ("PostgreSQL 16", "0.5-1 GB", "20 GB SSD", "Grafana metadata only (dashboards, users, settings); very low volume."),
        ("Alertmanager", "~100 MB", "< 1 GB", "Negligible."),
        ("Node Exporter", "~50 MB", "None", "Negligible."),
        ("OS + headroom", "2-3 GB", "40 GB", "RHEL 9, logs, buffers, backup staging."),
    ],
    [1900, 1900, 1700, 3860],
)

add_heading(doc, "2.1.2 Worked sizing example", 2)
add_body(doc, "Assume ~15 targets (GitLab, Jenkins, SonarQube, Nexus, plus their Node Exporters and a few Linux hosts), roughly 250,000 active series, a 30-second scrape interval, and 30-day retention.")
add_bullet(doc, "Ingestion: 250,000 series / 30 s = ~8,300 samples per second.")
add_bullet(doc, "Disk (Prometheus): retention_seconds x samples/s x bytes/sample. At ~8,300 samples/s and 1-2 bytes/sample this is roughly 1.0-1.4 GB/day. On the provisioned 50 GB /u01 mount, cap retention size at 40 GB (leaving ~20% headroom for WAL and compaction), which yields approximately 2-4 weeks of history at ~250,000 series - fewer days at higher cardinality.")
add_bullet(doc, "Memory: ~250,000 series x ~7.5 KiB is ~1.9 GB of head series, and Prometheus typically needs roughly twice that under load, so plan 4-6 GB for Prometheus alone. With Grafana, PostgreSQL, and the OS, 16 GB total leaves comfortable headroom.")
add_callout(doc, "Sizing basis", "Prometheus documents an average of 1-2 bytes stored per sample; memory scales with active series count. Recompute both figures from your real active-series count (Prometheus 'prometheus_tsdb_head_series' metric) after two weeks of production data, then adjust retention and RAM. Reducing series cardinality lowers storage more effectively than lengthening the scrape interval.", "note")

add_callout(doc, "Grafana database requirement", "Grafana supports PostgreSQL 12 or later (this runbook uses 16); SQLite is not recommended for production. Do not place Prometheus data on NFS - the TSDB requires a local POSIX-compliant filesystem.", "warning")

add_heading(doc, "2.2 Required organizational inputs", 2)
for item in [
    "One registered and patched RHEL 9 server with sudo access.",
    "Forward and reverse DNS for the monitoring server.",
    "User-facing Grafana DNS name and load balancer targeting the server on port 3000.",
    "TLS termination at the load balancer (or a certificate if Grafana-native TLS is chosen).",
    "Approved notification service and credentials.",
    "Firewall approvals for the port matrix below.",
    "Approved backup location with access controls and retention policy.",
    "Application-owner approval to enable metrics endpoints or install plugins/exporters.",
]:
    add_bullet(doc, item)

add_heading(doc, "2.3 Port matrix", 2)
add_table(
    doc,
    ["Source", "Destination", "Port", "Purpose"],
    [
        ("Organization load balancer", "Grafana on monitoring server", "3000/TCP", "Grafana HTTP (TLS terminated at LB)"),
        ("Approved admin networks", "Monitoring server SSH", "22/TCP", "Administration"),
        ("Prometheus (loopback)", "Alertmanager (loopback)", "9093/TCP", "Alert delivery, on-host"),
        ("Prometheus", "Node Exporter (this host + app servers)", "9100/TCP", "Host metrics"),
        ("Prometheus", "PostgreSQL exporter if added", "9187/TCP", "Optional DB metrics"),
        ("Prometheus", "Application endpoints", "Application-specific", "GitLab/Jenkins/SonarQube/Nexus metrics"),
    ],
    [2350, 2600, 1300, 3110],
)

add_callout(doc, "Security rule", "Do not expose Prometheus, Alertmanager, Node Exporter, or application metrics endpoints to public or general user networks. Bind them to loopback where possible and restrict remaining exporter ports to the monitoring server address and approved administrators.", "warning")

add_heading(doc, "3. Base RHEL 9 preparation", 1)
add_heading(doc, "3.1 Confirm the host", 2)
add_code(doc, """
cat /etc/redhat-release
uname -m
hostname -f
df -h
free -h
timedatectl
chronyc tracking
""")
add_body(doc, "Confirm that `uname -m` returns `x86_64`. The binary URLs in this runbook are for AMD64/x86_64.")
add_code(doc, """
sudo dnf update -y
sudo dnf install -y curl wget tar gzip unzip vim policycoreutils-python-utils
sudo systemctl reboot
""")
add_callout(doc, "Change control", "Schedule and approve the RHEL patching and reboot. Reconnect after the server returns, then confirm the expected kernel and services.", "warning")

add_heading(doc, "3.2 Create data and backup mount points", 2)
add_body(doc, "This deployment uses a dedicated 50 GB filesystem mounted at `/u01` for Prometheus time-series data. Confirm it is present, a real mount (not a directory on the root filesystem), and local (not NFS). PostgreSQL keeps its small default location and backups are written off this host.")
add_code(doc, """
findmnt /u01
df -hT /u01
sudo install -d -o root -g root -m 0755 /u01/prometheus
sudo install -d -o root -g root -m 0750 /var/backups/monitoring
sudo install -d -o root -g root -m 0755 /etc/monitoring
""")
add_callout(doc, "Storage sizing note", "50 GB is below the 100 GB+ that is comfortable for 30-day retention at moderate cardinality. On this mount, size Prometheus retention to roughly 40 GB and expect approximately 2-4 weeks of history depending on active-series count. Do not stage database or metric backups on /u01 - keep them off-host so a full or failed /u01 does not also lose the backups. See Section 2.1.2.", "warning")

add_heading(doc, "3.3 Confirm SELinux and firewall state", 2)
add_code(doc, """
getenforce
sudo firewall-cmd --state
sudo firewall-cmd --get-active-zones
""")
add_body(doc, "Keep SELinux enforcing. Do not disable SELinux to solve a configuration error. Add only the required SELinux policy or boolean after confirming the denied operation.")

page_break(doc)

# ------------------------------------------------- 4. PostgreSQL
add_heading(doc, "4. Install PostgreSQL 16", 1)
add_callout(doc, "Database role", "PostgreSQL is the Grafana backend on the same host. Grafana connects over the loopback interface, so the database listens only on 127.0.0.1 and is never exposed to the network.", "note")

add_heading(doc, "4.1 Install packages", 2)
add_code(doc, """
sudo dnf module reset postgresql -y
sudo dnf module install postgresql:16/server -y
postgres --version
""")

add_heading(doc, "4.2 Initialize the database", 2)
add_code(doc, """
sudo PGSETUP_INITDB_OPTIONS="--data-checksums" postgresql-setup --initdb
sudo -u postgres pg_controldata /var/lib/pgsql/data | grep "Data page checksum"
""")
add_body(doc, "Expected result: `Data page checksum version` is non-zero.")

add_heading(doc, "4.3 Configure PostgreSQL", 2)
add_body(doc, "Edit `/var/lib/pgsql/data/postgresql.conf` and set:")
add_code(doc, """
listen_addresses = 'localhost'
port = 5432
password_encryption = 'scram-sha-256'
max_connections = 200
shared_buffers = '512MB'
log_connections = on
log_disconnections = on
log_line_prefix = '%m [%p] %u@%d %r '
""")
add_body(doc, "Append the following to `/var/lib/pgsql/data/pg_hba.conf`. Loopback-only, SCRAM-authenticated access for the Grafana role:")
add_code(doc, """
host  grafana  grafana  127.0.0.1/32  scram-sha-256
host  grafana  grafana  ::1/128       scram-sha-256
""")
add_callout(doc, "Optional TLS", "Loopback database traffic does not traverse the network, so plaintext on 127.0.0.1 is acceptable for most policies. If local TLS is mandated, install server.crt/server.key/root.crt into /var/lib/pgsql/data, set ssl = on, and use ssl_mode = verify-full in grafana.ini (Section 8.4).", "note")

add_heading(doc, "4.4 Start and create the Grafana role and database", 2)
add_code(doc, """
sudo systemctl enable --now postgresql
sudo systemctl status postgresql --no-pager
sudo -u postgres psql -c "SELECT version();"
""")
add_body(doc, "Open a PostgreSQL administrator session:")
add_code(doc, """
sudo -u postgres psql
""")
add_body(doc, "At the `psql` prompt, run:")
add_code(doc, """
CREATE ROLE grafana LOGIN;
\\password grafana

CREATE DATABASE grafana
  OWNER grafana
  ENCODING 'UTF8'
  TEMPLATE template0;

\\q
""")
add_callout(doc, "Password handling", "Use a strong, unique password supplied by the approved secret-management process. Do not place passwords directly in shell commands, tickets, source control, or this document.", "warning")

add_heading(doc, "4.5 Verify connectivity", 2)
add_code(doc, """
psql "host=127.0.0.1 port=5432 dbname=grafana user=grafana" -c "SELECT current_database();"
""")
add_body(doc, "Expected: the command prompts for the Grafana password and returns `grafana`.")

page_break(doc)

# ------------------------------------------------- 5. Node Exporter
add_heading(doc, "5. Install Node Exporter", 1)
add_body(doc, "Install Node Exporter on the monitoring server and later repeat the same procedure on every approved Linux application server.")
add_heading(doc, "5.1 Download and verify", 2)
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
""")

add_heading(doc, "5.2 Create the service", 2)
add_code(doc, """
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
""")

add_heading(doc, "5.3 Firewall", 2)
add_body(doc, "On each Node Exporter host, allow TCP 9100 only from the monitoring server address.")
add_code(doc, """
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" \
  source address="<MON_IP>/32" port protocol="tcp" port="9100" accept'
sudo firewall-cmd --reload
""")
add_body(doc, "On the monitoring server itself, Prometheus reaches Node Exporter over localhost, so no external rule is required for the local exporter.")

page_break(doc)

# ------------------------------------------------- 6. Prometheus
add_heading(doc, "6. Install Prometheus LTS", 1)
add_heading(doc, "6.1 Download and verify", 2)
add_code(doc, """
cd /tmp
curl -fLO https://github.com/prometheus/prometheus/releases/download/v3.13.1/\
prometheus-3.13.1.linux-amd64.tar.gz

echo "962b812371aff838d152b6ff2d56fdb7a6396f5542f48ebf73421b9721f0d103  \
prometheus-3.13.1.linux-amd64.tar.gz" | sha256sum -c -

tar -xzf prometheus-3.13.1.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin prometheus
sudo install -d -o prometheus -g prometheus -m 0750 \
  /etc/prometheus /etc/prometheus/rules
sudo chown prometheus:prometheus /u01/prometheus
sudo chmod 0750 /u01/prometheus
sudo restorecon -Rv /u01/prometheus
sudo install -m 0755 prometheus-3.13.1.linux-amd64/prometheus \
  /usr/local/bin/prometheus
sudo install -m 0755 prometheus-3.13.1.linux-amd64/promtool \
  /usr/local/bin/promtool
""")
add_body(doc, "The Prometheus TSDB lives on the dedicated `/u01` mount (`/u01/prometheus`). The `restorecon` step applies the default SELinux context to the data directory.")

add_heading(doc, "6.2 Prometheus configuration", 2)
add_body(doc, "Create `/etc/prometheus/prometheus.yml`. Targets on this host use localhost; application servers use their addresses.")
add_code(doc, """
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
""")

add_heading(doc, "6.3 Initial alert rules", 2)
add_body(doc, "Create `/etc/prometheus/rules/infrastructure.yml`:")
add_code(doc, """
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
""")

add_heading(doc, "6.4 Validate ownership and syntax", 2)
add_code(doc, """
sudo chown -R prometheus:prometheus /etc/prometheus /u01/prometheus
sudo promtool check config /etc/prometheus/prometheus.yml
sudo promtool check rules /etc/prometheus/rules/infrastructure.yml
""")

add_heading(doc, "6.5 Create the Prometheus service", 2)
add_callout(doc, "Retention value", "Set <PROM_RETENTION_SIZE> to no more than approximately 80% of the /u01 filesystem so that WAL, compaction, and the head block have headroom. For the provisioned 50 GB mount, use 40GB. Both retention limits below apply together: whichever is reached first (30 days of time or 40 GB of size) triggers compaction of the oldest data.", "warning")
add_code(doc, """
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
""")

add_heading(doc, "6.6 Network access", 2)
add_body(doc, "Prometheus binds to 127.0.0.1 and is reached only by local Grafana. Do not expose the Prometheus UI on the network. For occasional admin access, use an SSH tunnel rather than opening port 9090.")

page_break(doc)

# ------------------------------------------------- 7. Alertmanager
add_heading(doc, "7. Install Alertmanager", 1)
add_heading(doc, "7.1 Download and verify", 2)
add_code(doc, """
cd /tmp
curl -fLO https://github.com/prometheus/alertmanager/releases/download/v0.33.1/\
alertmanager-0.33.1.linux-amd64.tar.gz

echo "93d802cba6a8d27239d747ce117df7648d326ab67394e32247540b030e9842ba  \
alertmanager-0.33.1.linux-amd64.tar.gz" | sha256sum -c -

tar -xzf alertmanager-0.33.1.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin alertmanager
sudo install -d -o alertmanager -g alertmanager -m 0750 \
  /etc/alertmanager /var/lib/alertmanager
sudo install -m 0755 alertmanager-0.33.1.linux-amd64/alertmanager \
  /usr/local/bin/alertmanager
sudo install -m 0755 alertmanager-0.33.1.linux-amd64/amtool \
  /usr/local/bin/amtool
""")

add_heading(doc, "7.2 Configure routing", 2)
add_body(doc, "Create `/etc/alertmanager/alertmanager.yml`. The initial null receiver is valid for build validation but must be replaced before go-live.")
add_code(doc, """
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
""")
add_callout(doc, "Go-live gate", "Production acceptance must fail until a test alert is successfully delivered to the approved notification channel and acknowledged by the support team.", "risk")

add_heading(doc, "7.3 Validate configuration", 2)
add_code(doc, """
sudo chown -R alertmanager:alertmanager \
  /etc/alertmanager /var/lib/alertmanager
sudo amtool check-config /etc/alertmanager/alertmanager.yml
""")

add_heading(doc, "7.4 Create the service", 2)
add_body(doc, "Clustering is disabled on a single node by passing an empty cluster listen address.")
add_code(doc, """
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
""")

page_break(doc)

# ------------------------------------------------- 8. Grafana
add_heading(doc, "8. Install Grafana OSS", 1)
add_heading(doc, "8.1 Add the official repository", 2)
add_code(doc, """
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
""")

add_heading(doc, "8.2 Create Grafana secrets", 2)
add_body(doc, "Store the database password and Grafana `secret_key` through the organizational secret-management process. Grafana reads them from files, so they never appear in grafana.ini.")
add_code(doc, """
sudo install -d -o root -g grafana -m 0750 /etc/grafana/secrets
sudo vi /etc/grafana/secrets/postgres_password
sudo vi /etc/grafana/secrets/secret_key
sudo chown root:grafana /etc/grafana/secrets/*
sudo chmod 0640 /etc/grafana/secrets/*
""")
add_body(doc, "Generate the secret key on an approved secure workstation and store it in the secret manager. It signs sessions and encrypts data-source secrets; keep it stable for the life of the database.")

add_heading(doc, "8.3 Configure Grafana", 2)
add_body(doc, "Edit `/etc/grafana/grafana.ini`. Grafana listens on port 3000 for the organization load balancer, which terminates TLS. `root_url` uses the external HTTPS name so links and redirects are correct.")
add_code(doc, """
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
""")
add_callout(doc, "TLS at the load balancer", "cookie_secure = true assumes users reach Grafana over HTTPS at the load balancer. Ensure the LB forwards X-Forwarded-Proto: https. If you must serve TLS on Grafana directly instead, set protocol = https, cert_file, and cert_key, then open 3000 only to approved sources.", "note")

add_heading(doc, "8.4 Provision the Prometheus data source", 2)
add_body(doc, "Grafana queries the local Prometheus directly over loopback.")
add_code(doc, """
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
""")

add_heading(doc, "8.5 Start Grafana", 2)
add_code(doc, """
sudo systemctl daemon-reload
sudo systemctl enable --now grafana-server
sudo systemctl status grafana-server --no-pager
curl -fsS http://127.0.0.1:3000/api/health
""")
add_body(doc, "Expected: database status is `ok`. Review logs if startup fails:")
add_code(doc, """
sudo journalctl -u grafana-server --since "30 minutes ago" --no-pager
""")

add_heading(doc, "8.6 Firewall for Grafana", 2)
add_body(doc, "Allow TCP 3000 only from the organization load balancer or approved user network.")
add_code(doc, """
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" \
  source address="<APPROVED_CIDR>" port protocol="tcp" port="3000" accept'
sudo firewall-cmd --reload
""")

page_break(doc)

# ------------------------------------------------- 9. Access
add_heading(doc, "9. External access, DNS, and load balancing", 1)
add_body(doc, "DNS and the load balancer are provided by the organization's network and platform teams and requested through the normal change process. Provide them the following so the request is unambiguous.")
add_table(
    doc,
    ["Requested item", "Value to supply"],
    [
        ("User-facing DNS name", "<GRAFANA_FQDN>"),
        ("Backend target", "<MON_IP>:3000 (HTTP)"),
        ("Protocol at the load balancer", "HTTPS/443 with organization TLS certificate"),
        ("Health check path", "/api/health (expects HTTP 200)"),
        ("Required forwarded header", "X-Forwarded-Proto: https"),
        ("Session affinity", "Not required (single backend)"),
        ("Allowed client networks", "<APPROVED_CIDR>"),
    ],
    [3200, 6160],
)
add_callout(doc, "Validation after LB is live", "Confirm that https://<GRAFANA_FQDN>/ loads the Grafana login, the certificate is valid, and the load-balancer health check reports healthy against /api/health.", "note")

add_heading(doc, "9.1 Initial login", 2)
add_body(doc, "Open `https://<GRAFANA_FQDN>/`. Sign in with `admin/admin`, then immediately replace the default password. Configure approved users and roles. If SSO is required, complete and test the organization's supported identity-provider integration before go-live.")

add_heading(doc, "10. Integrate application metrics", 1)
add_heading(doc, "10.1 Linux host metrics", 2)
add_body(doc, "Install Node Exporter (Section 5) on each GitLab, Jenkins, SonarQube, and Nexus Linux server. Restrict port 9100 to the monitoring server IP address. Add each target to the Prometheus configuration.")

add_heading(doc, "10.2 GitLab Self-Managed", 2)
for item in [
    "Confirm the GitLab installation method and version.",
    "Use GitLab's built-in Prometheus metrics and bundled exporters where supported.",
    "Allow only the monitoring server address in the metrics allowlist.",
    "Do not expose unauthenticated exporters outside the monitoring network.",
    "Collect GitLab, Sidekiq, Gitaly, Workhorse, PostgreSQL, Redis, Registry, and node metrics as applicable.",
]:
    add_bullet(doc, item)

add_heading(doc, "10.3 Jenkins", 2)
for item in [
    "Install the Jenkins Prometheus Metrics plugin through the approved plugin process.",
    "Confirm the plugin supports the installed Jenkins controller version.",
    "Validate the default `/prometheus/` endpoint, including its required trailing slash.",
    "Use Jenkins authentication and network restrictions consistent with organizational policy.",
    "Validate job status, duration, executor, queue, JVM, and controller metrics before dashboard acceptance.",
]:
    add_bullet(doc, item)

add_heading(doc, "10.4 SonarQube", 2)
for item in [
    "Use `/api/monitoring/metrics` for supported operational metrics and secure it with the configured Sonar system passcode.",
    "Use `/api/measures` for project code-quality values and histories.",
    "Because code-quality API responses are not identical to ordinary Prometheus scraping, use an approved API exporter or collection process where required.",
    "Also collect CPU, memory, disk, and Java process metrics through Node Exporter and approved JMX collection.",
]:
    add_bullet(doc, item)

add_heading(doc, "10.5 Nexus Repository", 2)
for item in [
    "For Nexus Repository 3.81 or later, use `/service/rest/metrics/prometheus`.",
    "For earlier supported releases, validate `/service/metrics/prometheus`.",
    "Use a dedicated account with the `nx-metrics-all` privilege.",
    "Use synthetic HTTP checks for required artifact or repository availability because native instance metrics may not prove that a specific artifact can be downloaded.",
]:
    add_bullet(doc, item)

add_heading(doc, "10.6 Safe rollout procedure", 2)
for number, text in enumerate([
    "Enable one application endpoint at a time.",
    "Validate the endpoint locally on the application server.",
    "Validate network access from the monitoring server.",
    "Add the target to the Prometheus configuration.",
    "Run `promtool check config`.",
    "Reload Prometheus during the approved window.",
    "Confirm the target is `UP`.",
    "Validate metrics with the application owner before creating alerts.",
], start=1):
    add_number(doc, text, number)

page_break(doc)

# ------------------------------------------------- 11. Backups
add_heading(doc, "11. Backups and recovery", 1)
add_callout(doc, "Primary recovery control", "Backups are the recovery path for this platform. Treat backup success and restore rehearsals as go-live gates, not optional hardening.", "risk")
add_heading(doc, "11.1 What must be backed up", 2)
add_table(
    doc,
    ["Artifact", "Backup method", "Frequency"],
    [
        ("Grafana PostgreSQL database", "Nightly `pg_dump` into approved backup storage", "Daily and before upgrades"),
        ("PostgreSQL configuration", "Protected file backup", "After every approved change"),
        ("Grafana configuration and provisioning", "Protected backup and source control without secrets", "After every change"),
        ("Grafana plugins", "Package/plugin inventory; reinstall from approved source", "After plugin change"),
        ("Prometheus/Alertmanager configuration", "Private source control", "After every change"),
        ("Prometheus data", "Optional TSDB snapshot if metric history must be retained", "Policy dependent"),
        ("Secrets and TLS material", "PKI/secret-management system", "According to policy"),
    ],
    [2700, 4300, 2360],
)

add_heading(doc, "11.2 PostgreSQL logical backup", 2)
add_body(doc, "Run using an approved protected path:")
add_code(doc, """
sudo -u postgres pg_dump \
  --format=custom \
  --file=<BACKUP_PATH>/grafana_$(date +%F_%H%M).dump \
  grafana

sudo -u postgres pg_restore --list \
  <BACKUP_PATH>/<GRAFANA_BACKUP_FILE>.dump | head
""")
add_body(doc, "Copy backups off the monitoring server. A backup on the same failed host is not a recovery option.")

add_heading(doc, "11.3 Configuration backup", 2)
add_code(doc, """
sudo tar --xattrs --selinux -czf \
  <BACKUP_PATH>/monitoring-config_$(date +%F_%H%M).tgz \
  /etc/grafana \
  /etc/prometheus \
  /etc/alertmanager \
  /etc/systemd/system/prometheus.service \
  /etc/systemd/system/alertmanager.service \
  /etc/systemd/system/node_exporter.service
""")
add_callout(doc, "Sensitive content", "The archive contains secrets and private configuration. Encrypt it, tightly restrict access, and never attach it to an ordinary ticket.", "warning")

add_heading(doc, "11.4 Restore test", 2)
for item in [
    "Perform a scheduled restore to a non-production PostgreSQL instance.",
    "Validate Grafana startup against the restored database.",
    "Confirm dashboards, users, data sources, and permissions.",
    "Record restoration time and compare it with the recovery-time objective.",
    "Correct the procedure after every failed or incomplete restore test.",
]:
    add_bullet(doc, item)

add_heading(doc, "11.5 Rebuild after host loss", 2)
for number, text in enumerate([
    "Provision a replacement RHEL 9 host and complete Sections 3 through 8.",
    "Before starting Grafana, restore the PostgreSQL database from the latest backup.",
    "Restore the configuration archive and reconcile secrets from the secret manager.",
    "Start services, confirm /api/health reports database `ok`, and validate dashboards.",
    "Request the load balancer to re-point <GRAFANA_FQDN> to the new host address.",
], start=1):
    add_number(doc, text, number)

page_break(doc)

# ------------------------------------------------- 12. Validation
add_heading(doc, "12. Production validation and acceptance", 1)
add_heading(doc, "12.1 Service validation", 2)
add_code(doc, """
sudo systemctl is-active postgresql
sudo systemctl is-active prometheus
sudo systemctl is-active alertmanager
sudo systemctl is-active node_exporter
sudo systemctl is-active grafana-server

curl -fsS http://localhost:9090/-/ready
curl -fsS http://localhost:9093/-/ready
curl -fsS http://localhost:9100/metrics | head
curl -fsS http://127.0.0.1:3000/api/health
""")

add_heading(doc, "12.2 Acceptance checklist", 2)
checks = [
    "Prometheus shows all required targets as UP.",
    "Prometheus evaluates the expected alert-rule set without errors.",
    "Alertmanager is running and reachable on loopback 9093.",
    "A test alert is delivered and acknowledged through the approved notification channel.",
    "Grafana reports database status `ok` and loads the Prometheus data source.",
    "All monitoring services are enabled and return automatically after a reboot.",
    "Grafana is reachable through the organization load balancer at https://<GRAFANA_FQDN>/.",
    "The load-balancer TLS certificate is valid and the health check passes.",
    "Default administrator credentials have been replaced.",
    "Anonymous access and user self-registration are disabled.",
    "Exporter and application metrics ports are restricted to the monitoring server.",
    "Backups complete successfully and a restoration test has passed.",
    "The operations team has the runbook, ownership matrix, and escalation contacts.",
]
for check in checks:
    add_bullet(doc, "☐ " + check)

add_heading(doc, "12.3 Failure tests", 2)
add_table(
    doc,
    ["Test", "Expected result", "Evidence"],
    [
        ("Stop then start Prometheus", "systemd restarts it; scraping resumes.", "Systemd status and Grafana query"),
        ("Block one Node Exporter", "TargetDown fires after configured delay.", "Prometheus alert and notification"),
        ("Reboot the monitoring server", "All enabled services return automatically.", "Systemd status and logs"),
        ("Restore PostgreSQL backup", "Grafana starts with expected data.", "Restore record and screenshots"),
        ("Simulate host loss rebuild", "Platform is recovered within the RTO.", "Timed rebuild record"),
    ],
    [2300, 4500, 2560],
)

page_break(doc)

# ------------------------------------------------- 13. Operations
add_heading(doc, "13. Operations, patching, and governance", 1)
add_heading(doc, "13.1 Daily checks", 2)
for item in [
    "Target availability and scrape errors.",
    "Prometheus disk usage, ingestion rate, query latency, and rule failures.",
    "Alertmanager health and notification errors.",
    "PostgreSQL health and disk usage.",
    "Grafana health, failed logins, data-source errors, and certificate expiry (at the LB).",
    "Confirmation that the most recent backup completed and was copied off-host.",
]:
    add_bullet(doc, item)

add_heading(doc, "13.2 Upgrade sequence", 2)
for number, text in enumerate([
    "Review release notes, security advisories, compatibility, and rollback requirements.",
    "Back up PostgreSQL and all configuration files.",
    "Schedule an approved maintenance window; expect a monitoring outage during the upgrade.",
    "Upgrade one component at a time and validate before the next.",
    "Upgrade active Grafana only after a verified database backup.",
    "Do not downgrade Grafana without restoring the pre-upgrade database backup.",
], start=1):
    add_number(doc, text, number)

add_heading(doc, "13.3 Configuration change sequence", 2)
add_code(doc, """
sudo promtool check config /etc/prometheus/prometheus.yml
sudo promtool check rules /etc/prometheus/rules/*.yml
sudo amtool check-config /etc/alertmanager/alertmanager.yml
sudo systemctl reload-or-restart prometheus alertmanager
""")
add_body(doc, "Validate configuration before reloading. Keep the previous known-good copy so a failed change can be reverted quickly.")

add_heading(doc, "13.4 Ownership", 2)
add_table(
    doc,
    ["Area", "Primary owner", "Required responsibilities"],
    [
        ("RHEL and storage", "Linux/platform team", "Patching, capacity, filesystem, service recovery"),
        ("PostgreSQL", "Database/platform team", "Backup, restore, capacity"),
        ("Grafana", "Monitoring team", "Users, dashboards, provisioning, upgrades"),
        ("Prometheus/Alertmanager", "Monitoring team", "Scrapes, rules, retention, notifications"),
        ("Application endpoints", "Application owners", "Metrics enablement and version compatibility"),
        ("Network/PKI/DNS/LB", "Infrastructure teams", "Firewall, certificates, names, load balancer"),
        ("Incident response", "Operations", "Acknowledgment, escalation, runbook execution"),
    ],
    [1950, 2200, 5210],
)

page_break(doc)

# ------------------------------------------------- 14. Blackbox Exporter
add_heading(doc, "14. Install Blackbox Exporter (front-door probes)", 1)
add_body(doc, "Blackbox Exporter lets Prometheus probe an endpoint from the outside - confirming that HTTPS and SSH actually answer - rather than only trusting a service's own metrics. It runs on the monitoring server, binds to loopback, and is queried by Prometheus. It is used in Section 15 to verify that developers can reach GitLab.")

add_heading(doc, "14.1 Download and verify", 2)
add_code(doc, """
cd /tmp
curl -fLO https://github.com/prometheus/blackbox_exporter/releases/download/v0.28.0/\
blackbox_exporter-0.28.0.linux-amd64.tar.gz

echo "caf5d242fb1cf6d5cb678f3f799f22703d4fafea26b03dcbbd7e1f1825e06329  \
blackbox_exporter-0.28.0.linux-amd64.tar.gz" | sha256sum -c -

tar -xzf blackbox_exporter-0.28.0.linux-amd64.tar.gz
sudo useradd --system --no-create-home --shell /sbin/nologin blackbox_exporter
sudo install -d -o blackbox_exporter -g blackbox_exporter -m 0750 /etc/blackbox_exporter
sudo install -m 0755 blackbox_exporter-0.28.0.linux-amd64/blackbox_exporter \
  /usr/local/bin/blackbox_exporter
""")

add_heading(doc, "14.2 Probe modules", 2)
add_body(doc, "Create `/etc/blackbox_exporter/blackbox.yml`:")
add_code(doc, """
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
""")

add_heading(doc, "14.3 Create the service", 2)
add_code(doc, """
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
ExecStart=/usr/local/bin/blackbox_exporter \
  --config.file=/etc/blackbox_exporter/blackbox.yml \
  --web.listen-address=127.0.0.1:9115
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
""")
add_body(doc, "Blackbox Exporter binds to `127.0.0.1:9115`. It makes outbound probe connections to targets but is only queried locally by Prometheus, so it needs no inbound firewall rule.")

page_break(doc)

# ------------------------------------------------- 15. GitLab (SCM) monitoring
add_heading(doc, "15. GitLab monitoring (SCM-only)", 1)
add_body(doc, "This section monitors a self-managed GitLab Omnibus server used only as source control (git hosting) - no CI/CD, runners, or registry in scope. GitLab Omnibus already bundles all required Prometheus exporters; they only need to be exposed to this monitoring server. Nothing is installed on GitLab.")
add_callout(doc, "Access split", "Section 15.2 is a change request for the GitLab platform owners (edits gitlab.rb). Sections 15.3-15.5 are performed on this monitoring server. If the GitLab team can expose only a subset, insist on Tier 1 first: node/disk, Gitaly, and the monitoring allowlist entry.", "note")

add_heading(doc, "15.1 Placeholders and exposed endpoints", 2)
add_table(
    doc,
    ["Placeholder", "Meaning", "Example"],
    [
        ("<GITLAB_IP>", "GitLab server address", "10.10.10.20"),
        ("<GITLAB_FQDN>", "GitLab URL host", "gitlab.example.com"),
        ("<GIT_DATA_MOUNT>", "Filesystem holding git repos", "/var/opt/gitlab"),
    ],
    [2600, 3760, 3000],
)
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
    [2400, 900, 4260, 1800],
)

add_heading(doc, "15.2 Change request for the GitLab owners", 2)
add_body(doc, "Provide the following to the GitLab platform team. Edit `/etc/gitlab/gitlab.rb`:")
add_code(doc, """
# --- Allow the monitoring server to read health/metrics endpoints ---
gitlab_rails['monitoring_whitelist'] = ['127.0.0.0/8', '<MON_IP>/32']

# --- Tier 1: host + git engine + rails health ---
node_exporter['listen_address']   = '<GITLAB_IP>:9100'
gitlab_exporter['listen_address'] = '<GITLAB_IP>'
gitlab_exporter['listen_port']    = '9168'
gitaly['configuration'] = {
  prometheus_listen_addr: '<GITLAB_IP>:9236',
}
# Older GitLab syntax if the hash form is rejected:
# gitaly['prometheus_listen_addr'] = '<GITLAB_IP>:9236'

# --- Tier 2: supporting services ---
gitlab_workhorse['prometheus_listen_addr'] = '<GITLAB_IP>:9229'
puma['exporter_enabled']  = true
puma['exporter_address']  = '<GITLAB_IP>'
puma['exporter_port']     = 8083
sidekiq['metrics_enabled'] = true
sidekiq['listen_address']  = '<GITLAB_IP>'
sidekiq['listen_port']     = 8082
postgres_exporter['listen_address'] = '<GITLAB_IP>:9187'
redis_exporter['listen_address']    = '<GITLAB_IP>:9121'
""")
add_body(doc, "Apply the change, then restrict the ports to this monitoring server only:")
add_code(doc, """
sudo gitlab-ctl reconfigure

for p in 9100 9236 9168 9229 8083 8082 9187 9121; do
  sudo firewall-cmd --permanent --add-rich-rule="rule family=\\"ipv4\\" \
    source address=\\"<MON_IP>/32\\" port protocol=\\"tcp\\" port=\\"$p\\" accept"
done
sudo firewall-cmd --reload
""")
add_callout(doc, "Security", "Binding to <GITLAB_IP> plus the firewall rule keeps these endpoints on the internal network and reachable only from <MON_IP>. Never expose GitLab exporter ports publicly.", "warning")
add_body(doc, "Ask the GitLab team to confirm the repository storage mount so alerts target the right disk:")
add_code(doc, """
df -h /var/opt/gitlab/git-data
""")

add_heading(doc, "15.3 Add GitLab scrape jobs (on the monitoring server)", 2)
add_body(doc, "Append to `scrape_configs:` in `/etc/prometheus/prometheus.yml`. Start with Tier 1; add Tier 2 once exposed.")
add_code(doc, """
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
""")

add_heading(doc, "15.4 Front-door probes (blackbox)", 2)
add_body(doc, "Add these jobs so Prometheus proves HTTPS and SSH actually answer - the truest 'can a developer reach git' signal. Requires Section 14.")
add_code(doc, """
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
""")
add_body(doc, "Validate and reload, then confirm the targets are UP:")
add_code(doc, """
sudo promtool check config /etc/prometheus/prometheus.yml
sudo systemctl reload-or-restart prometheus
curl -s 'http://127.0.0.1:9090/api/v1/query?query=up{service="gitlab"}'
""")

add_heading(doc, "15.5 SCM-focused alert rules", 2)
add_callout(doc, "Verify metric names", "Metric names vary slightly by GitLab version. After scraping starts, confirm each metric exists in the target's /metrics before trusting the rule.", "warning")
add_body(doc, "Create `/etc/prometheus/rules/gitlab.yml`:")
add_code(doc, """
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
        expr: 100 * node_filesystem_avail_bytes{service="gitlab",mountpoint="<GIT_DATA_MOUNT>"}
              / node_filesystem_size_bytes{service="gitlab",mountpoint="<GIT_DATA_MOUNT>"} < 15
        for: 15m
        labels: { severity: critical }
        annotations:
          summary: "GitLab repo disk <15% free on {{ $labels.instance }}"

      - alert: GitalyErrors
        expr: sum by (grpc_method)
              (rate(grpc_server_handled_total{job="gitlab-gitaly",grpc_code!="OK"}[5m])) > 0
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "Gitaly errors on {{ $labels.grpc_method }} (clone/push may fail)"

      - alert: GitalyHighLatency
        expr: histogram_quantile(0.99,
              sum by (le) (rate(grpc_server_handling_seconds_bucket{job="gitlab-gitaly"}[5m]))) > 1
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
""")
add_code(doc, """
sudo promtool check rules /etc/prometheus/rules/gitlab.yml
sudo systemctl reload-or-restart prometheus
""")

add_heading(doc, "15.6 Grafana dashboards", 2)
add_body(doc, "Use the existing Prometheus data source, not the GitLab data-source plugin (that plugin queries the GitLab API for engineering activity and is out of scope for SCM health). Import GitLab's official dashboards from grafana.com (search 'GitLab Omnibus' / 'Gitaly'), or build panels from these queries:")
add_bullet(doc, "Git RPC rate: sum(rate(grpc_server_handled_total{job=\"gitlab-gitaly\"}[5m])) by (grpc_method)")
add_bullet(doc, "Git RPC errors: sum(rate(grpc_server_handled_total{job=\"gitlab-gitaly\",grpc_code!=\"OK\"}[5m]))")
add_bullet(doc, "Component up/down: up{service=\"gitlab\"}")
add_bullet(doc, "Repo disk free %: 100 * node_filesystem_avail_bytes{service=\"gitlab\",mountpoint=\"<GIT_DATA_MOUNT>\"} / node_filesystem_size_bytes{...}")
add_bullet(doc, "Front-door reachability: probe_success{job=~\"gitlab-blackbox.*\"}")

add_heading(doc, "15.7 Acceptance", 2)
for item in [
    "GitLab owners applied 15.2 and gitlab-ctl reconfigure succeeded.",
    "All gitlab-* targets show UP in Prometheus.",
    "GitLabComponentDown tested: stop one exporter, alert fires, notification received.",
    "Repo disk alert points at the confirmed <GIT_DATA_MOUNT>.",
    "Blackbox HTTPS and SSH probes report probe_success == 1.",
    "Grafana dashboard renders git RPC, disk, and component health.",
    "A test SSH clone and HTTPS clone both succeed while dashboards show traffic.",
]:
    add_bullet(doc, "\u2610 " + item)
add_body(doc, "Out of scope (SCM-only): CI/CD pipeline metrics, runner fleet, container registry, and DORA/engineering-activity metrics. Add later only if GitLab usage expands.")

page_break(doc)

# ------------------------------------------------- Appendices
add_heading(doc, "Appendix A — Command and configuration inventory", 1)
add_table(
    doc,
    ["Component", "Configuration", "Data", "Service"],
    [
        ("PostgreSQL", "/var/lib/pgsql/data/*.conf", "/var/lib/pgsql/data", "postgresql"),
        ("Grafana", "/etc/grafana/grafana.ini", "PostgreSQL database", "grafana-server"),
        ("Grafana provisioning", "/etc/grafana/provisioning", "N/A", "grafana-server"),
        ("Prometheus", "/etc/prometheus", "/u01/prometheus", "prometheus"),
        ("Alertmanager", "/etc/alertmanager", "/var/lib/alertmanager", "alertmanager"),
        ("Node Exporter", "systemd unit", "N/A", "node_exporter"),
        ("Blackbox Exporter", "/etc/blackbox_exporter/blackbox.yml", "N/A", "blackbox_exporter"),
    ],
    [2100, 2900, 2100, 2260],
)

add_heading(doc, "Appendix B — Troubleshooting quick reference", 1)
add_table(
    doc,
    ["Symptom", "Checks"],
    [
        ("Grafana database error", "Test PostgreSQL login on 127.0.0.1; inspect Grafana logs; verify password file, ssl_mode, and pg_hba.conf."),
        ("Grafana dashboard has no data", "Check Prometheus readiness on 9090; confirm the data source URL is http://127.0.0.1:9090; inspect target status."),
        ("Prometheus will not start", "Run promtool; check ownership, retention value, disk space, and systemd logs."),
        ("Target DOWN", "Test the endpoint from the monitoring server; check firewall, authentication, certificate, and application health."),
        ("No notifications", "Check Alertmanager health, the receiver configuration, and the approved channel credentials."),
        ("Grafana unreachable via URL", "Confirm Grafana listens on 0.0.0.0:3000, firewall allows the LB, and the load balancer health check passes."),
        ("Login redirects to wrong scheme", "Confirm root_url uses https and the LB forwards X-Forwarded-Proto: https."),
    ],
    [2800, 6560],
)

add_heading(doc, "Appendix C — Authoritative references", 1)
refs = [
    ("Grafana RHEL installation", "https://grafana.com/docs/grafana/latest/setup-grafana/installation/redhat-rhel-fedora/"),
    ("Grafana configuration", "https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/"),
    ("Grafana database setup", "https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#database"),
    ("Grafana backup", "https://grafana.com/docs/grafana/latest/administration/back-up-grafana/"),
    ("Prometheus downloads", "https://prometheus.io/download/"),
    ("Prometheus storage", "https://prometheus.io/docs/prometheus/latest/storage/"),
    ("Prometheus security model", "https://prometheus.io/docs/operating/security/"),
    ("Alertmanager configuration", "https://prometheus.io/docs/alerting/latest/configuration/"),
    ("RHEL 9 PostgreSQL installation", "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_database_servers/using-postgresql_configuring-and-using-database-servers"),
    ("PostgreSQL backup and restore", "https://www.postgresql.org/docs/16/backup.html"),
    ("GitLab Prometheus monitoring", "https://docs.gitlab.com/administration/monitoring/prometheus/"),
    ("Jenkins Prometheus plugin", "https://plugins.jenkins.io/prometheus/"),
    ("SonarQube Web API", "https://docs.sonarsource.com/sonarqube-server/extension-guide/web-api"),
    ("Nexus Prometheus metrics", "https://help.sonatype.com/en/prometheus.html"),
]
for label, url in refs:
    p = doc.add_paragraph(style="Normal")
    r = p.add_run(label + ": ")
    set_run_font(r, bold=True, size=10)
    r = p.add_run(url)
    set_run_font(r, size=9.5, color=BLUE2)

add_callout(doc, "Version note", "This runbook pins Prometheus 3.13.1 LTS (supported to 31 July 2027), Alertmanager 0.33.1, and Node Exporter 1.12.1, verified against the official release checksums on 23 July 2026. The earlier 3.5 LTS line reaches end of support on 31 July 2026 and should not be used for a new build. Revalidate versions and checksums immediately before production installation.", "note")

# Document properties and final XML settings.
doc.core_properties.title = "Grafana Monitoring Platform Production Installation Runbook"
doc.core_properties.subject = "RHEL 9 production monitoring deployment"
doc.core_properties.author = "Platform Engineering"
doc.core_properties.keywords = "Grafana, Prometheus, Alertmanager, PostgreSQL, RHEL 9, Node Exporter"

settings = doc.settings._element
update_fields = settings.find(qn("w:updateFields"))
if update_fields is None:
    update_fields = OxmlElement("w:updateFields")
    settings.append(update_fields)
update_fields.set(qn("w:val"), "true")

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
