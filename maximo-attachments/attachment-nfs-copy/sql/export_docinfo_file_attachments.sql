-- Export Maximo file-based attachment paths from DOCINFO.
--
-- Usage from SQL*Plus:
--   sqlplus -L 'maximo/password@//db-host:1521/service'
--   SQL> @attachment-nfs-copy/sql/export_docinfo_file_attachments.sql /tmp/maximo_docinfo_file_attachments.psv
--
-- Output format:
--   pipe-separated values with a header row
--
-- Notes:
--   URLTYPE='FILE' rows are NFS/file attachments.
--   URLTYPE='URL' rows are external links and should not be copied from NFS.

set pagesize 0
set heading off
set feedback off
set verify off
set echo off
set linesize 32767
set trimspool on
set termout on

spool &1

prompt docinfoid|document|doctype|urltype|urlname

select
    docinfoid || '|' ||
    replace(replace(replace(nvl(document, ''), '|', ' '), chr(10), ' '), chr(13), ' ') || '|' ||
    replace(replace(replace(nvl(doctype, ''), '|', ' '), chr(10), ' '), chr(13), ' ') || '|' ||
    replace(replace(replace(nvl(urltype, ''), '|', ' '), chr(10), ' '), chr(13), ' ') || '|' ||
    replace(replace(replace(nvl(urlname, ''), '|', ' '), chr(10), ' '), chr(13), ' ')
from docinfo
where urltype = 'FILE'
  and urlname is not null
  and lower(urlname) like '/doclinks/%'
order by docinfoid;

spool off
exit
