# Maximo NFS Attachment Copy

Linux-only runbook for copying Maximo Manage attachments from Prod NFS to Dev/DR PowerScale NFS after a Prod database clone.

This is **not** S3 migration.

## What This Does

The cloned Dev/DR database has attachment records in `DOCINFO`, but the physical files still exist on Prod NFS. This process uses the database paths to copy the matching files into Dev/DR NFS.

It only copies files. It does not move, delete, rename, or update database records.

## Folder Contents

```text
scripts/build_manifest.sh       Builds source-to-destination mapping
scripts/copy_from_manifest.sh   Dry-runs or copies files from manifest
examples/                       Optional sample/export files
```

## 1. Export 3000 Attachment Paths From DBeaver

Run this SQL against the cloned Dev/DR database:

```sql
select
  docinfoid as "docinfoid",
  document as "document",
  doctype as "doctype",
  urltype as "urltype",
  urlname as "urlname"
from docinfo
where urltype = 'FILE'
  and urlname is not null
  and lower(urlname) like '/doclinks/%'
order by docinfoid desc
fetch first 3000 rows only;
```

Export from DBeaver:

```text
Format: CSV
Delimiter: |
Header: top
Quote character: "
Quote always: enabled
Encoding: UTF-8
File name: maximo_3000_attachments.csv
```

## 2. Export All Attachment Paths From DBeaver

For full copy, run the same query without the 3000-row limit:

```sql
select
  docinfoid as "docinfoid",
  document as "document",
  doctype as "doctype",
  urltype as "urltype",
  urlname as "urlname"
from docinfo
where urltype = 'FILE'
  and urlname is not null
  and lower(urlname) like '/doclinks/%'
order by docinfoid;
```

Export from DBeaver:

```text
Format: CSV
Delimiter: |
Header: top
Quote character: "
Quote always: enabled
Encoding: UTF-8
File name: maximo_all_attachments.csv
```

## 3. Prepare Linux Copy Server

Use a Linux server that can access both:

```text
Prod NFS doclinks path
Dev/DR NFS doclinks path
```

Create a working folder:

```bash
mkdir -p /var/tmp/maximo_attachment_copy
```

Copy the DBeaver export to:

```text
/var/tmp/maximo_attachment_copy/maximo_3000_attachments.csv
```

or for full copy:

```text
/var/tmp/maximo_attachment_copy/maximo_all_attachments.csv
```

## 4. Set Real NFS Paths

Set these on the Linux copy server:

```bash
PROD_ROOT="/actual/prod/doclinks"
DEV_ROOT="/actual/dev/doclinks"
WORK_DIR="/var/tmp/maximo_attachment_copy"
```

Example mapping:

```text
DB URLNAME:
  /doclinks/attachments/example.pdf

Prod source:
  $PROD_ROOT/attachments/example.pdf

Dev/DR destination:
  $DEV_ROOT/attachments/example.pdf
```

## 5. Build Manifest For 3000-File Test

```bash
./scripts/build_manifest.sh \
  "$WORK_DIR/maximo_3000_attachments.csv" \
  "$WORK_DIR/maximo_3000_manifest.csv" \
  "$PROD_ROOT" \
  "$DEV_ROOT"
```

Review:

```bash
grep source_missing "$WORK_DIR/maximo_3000_manifest.csv"
grep dest_exists_different_size "$WORK_DIR/maximo_3000_manifest.csv"
```

## 6. Dry-Run 3000-File Copy

```bash
./scripts/copy_from_manifest.sh \
  "$WORK_DIR/maximo_3000_manifest.csv" \
  "$WORK_DIR/maximo_3000_dryrun.log" \
  dry-run
```

Review:

```bash
grep DRY_RUN_READY "$WORK_DIR/maximo_3000_dryrun.log" | wc -l
grep SOURCE_MISSING "$WORK_DIR/maximo_3000_dryrun.log"
grep SKIPPED_DEST_DIFFERENT_SIZE "$WORK_DIR/maximo_3000_dryrun.log"
```

## 7. Execute 3000-File Copy

```bash
./scripts/copy_from_manifest.sh \
  "$WORK_DIR/maximo_3000_manifest.csv" \
  "$WORK_DIR/maximo_3000_copy.log" \
  execute
```

Review:

```bash
grep COPIED "$WORK_DIR/maximo_3000_copy.log" | wc -l
grep COPY_FAILED "$WORK_DIR/maximo_3000_copy.log"
grep SOURCE_MISSING "$WORK_DIR/maximo_3000_copy.log"
```

## 8. Build Manifest For Full Copy

```bash
./scripts/build_manifest.sh \
  "$WORK_DIR/maximo_all_attachments.csv" \
  "$WORK_DIR/maximo_all_manifest.csv" \
  "$PROD_ROOT" \
  "$DEV_ROOT"
```

Review:

```bash
grep source_missing "$WORK_DIR/maximo_all_manifest.csv"
grep dest_exists_different_size "$WORK_DIR/maximo_all_manifest.csv"
```

## 9. Dry-Run Full Copy

```bash
./scripts/copy_from_manifest.sh \
  "$WORK_DIR/maximo_all_manifest.csv" \
  "$WORK_DIR/maximo_all_dryrun.log" \
  dry-run
```

Review:

```bash
grep DRY_RUN_READY "$WORK_DIR/maximo_all_dryrun.log" | wc -l
grep SOURCE_MISSING "$WORK_DIR/maximo_all_dryrun.log"
grep SKIPPED_DEST_DIFFERENT_SIZE "$WORK_DIR/maximo_all_dryrun.log"
```

## 10. Execute Full Copy

Run only after dry-run review:

```bash
./scripts/copy_from_manifest.sh \
  "$WORK_DIR/maximo_all_manifest.csv" \
  "$WORK_DIR/maximo_all_copy.log" \
  execute
```

Review:

```bash
grep COPIED "$WORK_DIR/maximo_all_copy.log" | wc -l
grep COPY_FAILED "$WORK_DIR/maximo_all_copy.log"
grep SOURCE_MISSING "$WORK_DIR/maximo_all_copy.log"
```

## 11. Validate In Dev/DR Maximo

Open several copied attachments in Dev/DR Maximo:

```text
PDF
JPG/PNG
XLS/XLSX
DOC/DOCX
```

## Safety Notes

- Source Prod NFS files are never modified.
- The script uses `cp -p`, not `mv`.
- Destination folders are created automatically.
- Existing destination files with the same size are skipped.
- Existing destination files with different size are skipped for manual review.
