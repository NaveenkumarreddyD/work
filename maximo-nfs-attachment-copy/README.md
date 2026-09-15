# Maximo Attachment File Copy Procedure

## Purpose

After the Prod database is cloned to Dev/DR, Maximo has the attachment records in the database, but the actual attachment files still need to be copied from Prod NFS to the Dev/DR PowerScale NFS location.

This procedure uses the paths stored in `DOCINFO.URLNAME` to copy the matching files.

This process only copies files. It does not move files, delete files, change Prod NFS, or update database records.

## What You Need Before Starting

Confirm these items first:

- DBeaver can connect to the cloned Dev/DR Maximo database.
- You know the Prod NFS doclinks root path.
- You know the Dev/DR PowerScale NFS doclinks root path.
- The server where you run the scripts can access both NFS paths.
- The scripts in this folder are available on that server.

## Files In This Folder

```text
sql/export_3000_attachments.sql    SQL for testing with 3000 attachments
sql/export_all_attachments.sql     SQL for exporting all file attachments
scripts/build_manifest.sh          Creates the source-to-destination file list
scripts/copy_from_manifest.sh      Runs dry run or actual copy
```

## Common Setup

Create a working folder on the copy server:

```bash
mkdir -p /var/tmp/maximo_attachment_copy
```

Set your real NFS paths:

```bash
PROD_ROOT="/actual/prod/doclinks"
DEV_ROOT="/actual/dev/doclinks"
WORK_DIR="/var/tmp/maximo_attachment_copy"
```

Replace these example paths with the real paths for your environment.

Example mapping:

```text
Database path:
  /doclinks/attachments/example.pdf

Prod source file:
  $PROD_ROOT/attachments/example.pdf

Dev/DR destination file:
  $DEV_ROOT/attachments/example.pdf
```

## Option 1: Test With 3000 Attachments

Use this first to validate the process before copying everything.

### Step 1: Export 3000 Records From DBeaver

In DBeaver, run:

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

The same SQL is saved here:

```text
sql/export_3000_attachments.sql
```

Export the result from DBeaver using these settings:

```text
Format: CSV
Delimiter: |
Header: top
Quote character: "
Quote always: enabled
Encoding: UTF-8
File name: maximo_3000_attachments.csv
```

Copy the exported file to the copy server:

```text
/var/tmp/maximo_attachment_copy/maximo_3000_attachments.csv
```

### Step 2: Build The 3000-File Manifest

```bash
./scripts/build_manifest.sh \
  "$WORK_DIR/maximo_3000_attachments.csv" \
  "$WORK_DIR/maximo_3000_manifest.csv" \
  "$PROD_ROOT" \
  "$DEV_ROOT"
```

Review possible issues before copying:

```bash
grep source_missing "$WORK_DIR/maximo_3000_manifest.csv"
grep dest_exists_different_size "$WORK_DIR/maximo_3000_manifest.csv"
```

### Step 3: Dry Run The 3000-File Copy

```bash
./scripts/copy_from_manifest.sh \
  "$WORK_DIR/maximo_3000_manifest.csv" \
  "$WORK_DIR/maximo_3000_dryrun.log" \
  dry-run
```

Review the dry-run result:

```bash
grep DRY_RUN_READY "$WORK_DIR/maximo_3000_dryrun.log" | wc -l
grep SOURCE_MISSING "$WORK_DIR/maximo_3000_dryrun.log"
grep SKIPPED_DEST_DIFFERENT_SIZE "$WORK_DIR/maximo_3000_dryrun.log"
```

### Step 4: Copy The 3000 Files

Run this only after reviewing the dry run:

```bash
./scripts/copy_from_manifest.sh \
  "$WORK_DIR/maximo_3000_manifest.csv" \
  "$WORK_DIR/maximo_3000_copy.log" \
  execute
```

Review the copy result:

```bash
grep COPIED "$WORK_DIR/maximo_3000_copy.log" | wc -l
grep COPY_FAILED "$WORK_DIR/maximo_3000_copy.log"
grep SOURCE_MISSING "$WORK_DIR/maximo_3000_copy.log"
```

## Option 2: Copy All Attachments

Use this after the 3000-file test is successful.

### Step 1: Export All File Attachment Records From DBeaver

In DBeaver, run:

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

The same SQL is saved here:

```text
sql/export_all_attachments.sql
```

Export the result from DBeaver using these settings:

```text
Format: CSV
Delimiter: |
Header: top
Quote character: "
Quote always: enabled
Encoding: UTF-8
File name: maximo_all_attachments.csv
```

Copy the exported file to the copy server:

```text
/var/tmp/maximo_attachment_copy/maximo_all_attachments.csv
```

### Step 2: Build The Full Manifest

```bash
./scripts/build_manifest.sh \
  "$WORK_DIR/maximo_all_attachments.csv" \
  "$WORK_DIR/maximo_all_manifest.csv" \
  "$PROD_ROOT" \
  "$DEV_ROOT"
```

Review possible issues before copying:

```bash
grep source_missing "$WORK_DIR/maximo_all_manifest.csv"
grep dest_exists_different_size "$WORK_DIR/maximo_all_manifest.csv"
```

### Step 3: Dry Run The Full Copy

```bash
./scripts/copy_from_manifest.sh \
  "$WORK_DIR/maximo_all_manifest.csv" \
  "$WORK_DIR/maximo_all_dryrun.log" \
  dry-run
```

Review the dry-run result:

```bash
grep DRY_RUN_READY "$WORK_DIR/maximo_all_dryrun.log" | wc -l
grep SOURCE_MISSING "$WORK_DIR/maximo_all_dryrun.log"
grep SKIPPED_DEST_DIFFERENT_SIZE "$WORK_DIR/maximo_all_dryrun.log"
```

### Step 4: Copy All Files

Run this only after reviewing the dry run:

```bash
./scripts/copy_from_manifest.sh \
  "$WORK_DIR/maximo_all_manifest.csv" \
  "$WORK_DIR/maximo_all_copy.log" \
  execute
```

Review the copy result:

```bash
grep COPIED "$WORK_DIR/maximo_all_copy.log" | wc -l
grep COPY_FAILED "$WORK_DIR/maximo_all_copy.log"
grep SOURCE_MISSING "$WORK_DIR/maximo_all_copy.log"
```

## Validation

After copying, open sample attachments in Dev/DR Maximo.

Test different file types:

```text
PDF
JPG or PNG
XLS or XLSX
DOC or DOCX
```

Confirm the files open successfully from Dev/DR Maximo.

## Safety Notes

- Prod files are not modified.
- The copy script uses `cp -p`.
- Existing destination files with the same size are skipped.
- Existing destination files with a different size are skipped and logged for review.
- Missing source files are logged.
