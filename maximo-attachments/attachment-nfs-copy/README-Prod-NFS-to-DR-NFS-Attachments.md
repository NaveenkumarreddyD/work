# Prod NFS to Dev/DR NFS Attachment Copy

This runbook copies only the Maximo attachments referenced by the cloned Dev database.
It is meant for the case where Prod database was cloned to Dev/DR and `DOCINFO.URLNAME`
still points to file-based NFS attachments such as:

```text
/doclinks/attachments/example.pdf
```

## Goal

Copy approximately 3000 referenced attachments from Prod NFS to Dev/DR PowerScale NFS
while preserving the same relative `doclinks` structure.

## Important Idea

Do not copy the whole NFS share blindly. Use the database as the source of truth.

```text
DOCINFO.URLTYPE = FILE    copy from NFS
DOCINFO.URLTYPE = URL     do not copy, this is an external link
```

## Assumptions

Replace these example paths with your real mounts:

```text
Prod NFS doclinks root: /mnt/prod-doclinks
Dev/DR NFS doclinks root: /mnt/dev-doclinks
```

If `DOCINFO.URLNAME` is:

```text
/doclinks/attachments/test.pdf
```

Then this toolkit maps it to:

```text
Source: /mnt/prod-doclinks/attachments/test.pdf
Dest:   /mnt/dev-doclinks/attachments/test.pdf
```

## Step 1. Export Attachment Paths From Dev Database

Connect to the cloned Dev Oracle database with SQL*Plus:

```bash
sqlplus -L 'maximo/<password>@//<db-host>:1521/<service-name>'
```

Run the export SQL:

```sql
@maximo-attachments/attachment-nfs-copy/sql/export_docinfo_file_attachments.sql /tmp/maximo_docinfo_file_attachments.psv
```

This exports rows from `DOCINFO` where:

```text
URLTYPE = FILE
URLNAME starts with /doclinks/
```

## Step 2. Copy Export File To The Server Doing The NFS Copy

The next steps must run on a host/pod/server that can see both:

```text
Prod NFS attachment path
Dev/DR NFS attachment path
```

Example:

```bash
scp /tmp/maximo_docinfo_file_attachments.psv <copy-host>:/tmp/
```

## Step 3. Build A Manifest

Run from this repository folder:

```bash
python3 maximo-attachments/attachment-nfs-copy/scripts/build_attachment_manifest.py \
  --input /tmp/maximo_docinfo_file_attachments.psv \
  --output /tmp/maximo_attachment_copy_manifest.csv \
  --source-root /mnt/prod-doclinks \
  --dest-root /mnt/dev-doclinks \
  --url-prefix /doclinks
```

Review the summary:

```text
ready                         files ready to copy
source_missing                DB points to a file not found on Prod NFS
dest_exists_same_size         already copied or already present
dest_exists_different_size    investigate before overwrite
```

## Step 4. Dry-Run The Copy

```bash
python3 maximo-attachments/attachment-nfs-copy/scripts/copy_attachments_from_manifest.py \
  --manifest /tmp/maximo_attachment_copy_manifest.csv \
  --log /tmp/maximo_attachment_copy_dryrun.csv
```

No files are copied in dry-run mode.

## Step 5. Execute The Copy

```bash
python3 maximo-attachments/attachment-nfs-copy/scripts/copy_attachments_from_manifest.py \
  --manifest /tmp/maximo_attachment_copy_manifest.csv \
  --log /tmp/maximo_attachment_copy_execute.csv \
  --execute
```

The script creates destination folders and copies files with metadata preservation.

## Step 6. Validate

Check copy results:

```bash
grep ',missing_source,' /tmp/maximo_attachment_copy_execute.csv
grep ',error,' /tmp/maximo_attachment_copy_execute.csv
grep ',skipped_existing_different_size,' /tmp/maximo_attachment_copy_execute.csv
```

Open several attachments in Dev Maximo:

```text
PDF
JPG/PNG
XLS/XLSX
DOC/DOCX
```

## Step 7. Rerun If Needed

The copy script is rerunnable. If a file already exists with the same size, it skips it.

To overwrite different-size files, use:

```bash
python3 maximo-attachments/attachment-nfs-copy/scripts/copy_attachments_from_manifest.py \
  --manifest /tmp/maximo_attachment_copy_manifest.csv \
  --log /tmp/maximo_attachment_copy_overwrite.csv \
  --execute \
  --overwrite
```

Use overwrite only after reviewing the different-size rows.

## Engineer Checklist

- Prod DB has already been cloned to Dev.
- Dev Maximo points to the Dev/DR NFS doclinks location.
- Copy host can mount/read Prod NFS.
- Copy host can mount/write Dev/DR PowerScale NFS.
- `DOCINFO.URLTYPE='URL'` rows are excluded.
- Dry-run completed before actual copy.
- Missing source files are reviewed.
- File ownership/permissions on Dev/DR NFS allow Maximo pods to read attachments.
