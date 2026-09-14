# PowerScale S3 Bucket for IBM MAS Attachments

Small runbook for creating/fixing a PowerScale S3 bucket for IBM MAS Manage attachments.

## 1. Confirm the Bucket and S3 User

Bucket:

```text
dr-maximo-bckt
```

Backing path:

```text
/ifs/stl-pwrsc/data/S3/DR-Maximo-Bckt
```

S3 user:

```text
dr_maximo
```

Verify the S3 access key belongs to the same S3 user that has bucket access:

```bash
isi s3 keys list
isi s3 buckets view dr-maximo-bckt
```

The bucket owner / ACL and the access key user should line up with `dr_maximo`.

## 2. Enter the Correct Access Zone

Because `dr_maximo` is a local user in the `data` access zone, first find the zone ID:

```bash
isi zone zones view --zone=data
```

Then enter the zone context:

```bash
isi_run -z <ZONE_ID> -l root
```

Example:

```bash
isi_run -z 2 -l root
```

## 3. Set Bucket Directory Ownership

For a dedicated IBM MAS attachment bucket, set the bucket path owner/group:

```bash
chown dr_maximo:s3_mas_attach_users /ifs/stl-pwrsc/data/S3/DR-Maximo-Bckt
```

Use your real group name instead of `s3_mas_attach_users` if different.

## 4. Add Parent Directory Traverse Access

The user or group must be able to traverse each parent directory to reach the bucket path.

For group `s3_mas_attach_users`:

```bash
chmod +a group s3_mas_attach_users allow dir_gen_execute /ifs/stl-pwrsc
chmod +a group s3_mas_attach_users allow dir_gen_execute /ifs/stl-pwrsc/data
chmod +a group s3_mas_attach_users allow dir_gen_execute /ifs/stl-pwrsc/data/S3
```

Or for user `dr_maximo` directly:

```bash
chmod +a user dr_maximo allow dir_gen_execute /ifs/stl-pwrsc
chmod +a user dr_maximo allow dir_gen_execute /ifs/stl-pwrsc/data
chmod +a user dr_maximo allow dir_gen_execute /ifs/stl-pwrsc/data/S3
```

## 5. Add Bucket Directory Access

For group `s3_mas_attach_users`:

```bash
chmod +a group s3_mas_attach_users allow dir_gen_all,file_gen_all,object_inherit,container_inherit /ifs/stl-pwrsc/data/S3/DR-Maximo-Bckt
```

Or for user `dr_maximo` directly:

```bash
chmod +a user dr_maximo allow dir_gen_all,file_gen_all,object_inherit,container_inherit /ifs/stl-pwrsc/data/S3/DR-Maximo-Bckt
```

For an existing bucket with files already inside, apply recursively:

```bash
chmod -R +a group s3_mas_attach_users allow dir_gen_all,file_gen_all,object_inherit,container_inherit /ifs/stl-pwrsc/data/S3/DR-Maximo-Bckt
```

## 6. Set PowerScale S3 Bucket ACL

In the PowerScale S3 bucket UI or CLI, grant the MAS S3 user access:

```text
dr_maximo = FULL_CONTROL
```

PowerScale S3 needs both:

```text
S3 bucket ACL permission
OneFS filesystem permission on the backing path
```

## 7. Test with s3cmd

Use the same access key and secret that IBM MAS will use.

```bash
s3cmd ls s3://dr-maximo-bckt/
s3cmd put test.txt s3://dr-maximo-bckt/test.txt
s3cmd get s3://dr-maximo-bckt/test.txt
s3cmd del s3://dr-maximo-bckt/test.txt
```

If you still see `403 AccessDenied`, check:

```bash
s3cmd -d ls s3://dr-maximo-bckt/
ls -led /ifs/stl-pwrsc/data/S3/DR-Maximo-Bckt
id dr_maximo
```

## Notes

- Parent directories only need traverse/execute access.
- The bucket directory needs read/write/create/delete access for IBM MAS attachments.
- If using multiple MAS/S3 users, prefer group ACLs instead of adding each user directly.
- If users or groups exist only in the `data` access zone, run the ACL commands from `isi_run -z <ZONE_ID> -l root`.
