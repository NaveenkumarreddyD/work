#!/usr/bin/env python3
"""
Build a copy manifest from Maximo DOCINFO attachment export.

The input file is the pipe-separated output from:
  sql/export_docinfo_file_attachments.sql

The output manifest contains one row per attachment with resolved source and
destination paths, plus status fields for pre-copy validation.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


FIELDS = [
    "docinfoid",
    "document",
    "doctype",
    "urltype",
    "urlname",
    "relative_path",
    "source_path",
    "dest_path",
    "source_exists",
    "dest_exists",
    "source_size",
    "dest_size",
    "status",
]


def clean_root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def make_relative(urlname: str, url_prefix: str) -> str | None:
    prefix = url_prefix.rstrip("/")
    if not urlname.startswith(prefix + "/"):
        return None
    return urlname[len(prefix) + 1 :].lstrip("/")


def file_size(path: Path) -> int | str:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return ""


def build_status(source: Path, dest: Path) -> str:
    if not source.exists():
        return "source_missing"
    if dest.exists():
        if source.stat().st_size == dest.stat().st_size:
            return "dest_exists_same_size"
        return "dest_exists_different_size"
    return "ready"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="DOCINFO pipe-separated export file")
    parser.add_argument("--output", required=True, help="CSV manifest to write")
    parser.add_argument("--source-root", required=True, help="Prod NFS doclinks root, e.g. /mnt/prod/doclinks")
    parser.add_argument("--dest-root", required=True, help="Dev/DR NFS doclinks root, e.g. /mnt/dev/doclinks")
    parser.add_argument("--url-prefix", default="/doclinks", help="Prefix stored in DOCINFO.URLNAME")
    args = parser.parse_args()

    source_root = clean_root(args.source_root)
    dest_root = clean_root(args.dest_root)
    input_path = Path(args.input)
    output_path = Path(args.output)

    totals = {
        "rows": 0,
        "written": 0,
        "skipped_nonmatching_prefix": 0,
        "skipped_non_file": 0,
        "source_missing": 0,
        "ready": 0,
        "dest_exists_same_size": 0,
        "dest_exists_different_size": 0,
    }

    with input_path.open(newline="", encoding="utf-8") as src, output_path.open(
        "w", newline="", encoding="utf-8"
    ) as out:
        reader = csv.DictReader(src, delimiter="|")
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()

        for row in reader:
            totals["rows"] += 1
            urltype = (row.get("urltype") or "").strip()
            urlname = (row.get("urlname") or "").strip()

            if urltype != "FILE":
                totals["skipped_non_file"] += 1
                continue

            relative = make_relative(urlname, args.url_prefix)
            if relative is None:
                totals["skipped_nonmatching_prefix"] += 1
                continue

            source = source_root / relative
            dest = dest_root / relative
            status = build_status(source, dest)
            totals[status] += 1

            writer.writerow(
                {
                    "docinfoid": row.get("docinfoid", "").strip(),
                    "document": row.get("document", "").strip(),
                    "doctype": row.get("doctype", "").strip(),
                    "urltype": urltype,
                    "urlname": urlname,
                    "relative_path": relative,
                    "source_path": str(source),
                    "dest_path": str(dest),
                    "source_exists": str(source.exists()).lower(),
                    "dest_exists": str(dest.exists()).lower(),
                    "source_size": file_size(source),
                    "dest_size": file_size(dest),
                    "status": status,
                }
            )
            totals["written"] += 1

    print("Manifest written:", output_path)
    for key, value in totals.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
