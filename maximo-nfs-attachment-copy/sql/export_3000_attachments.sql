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
