#!/usr/bin/env bash
set -u

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <input_csv> <output_manifest> <source_root> <dest_root>"
  exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"
SOURCE_ROOT="${3%/}"
DEST_ROOT="${4%/}"

echo "docinfoid|urlname|source_path|dest_path|source_exists|dest_exists|source_size|dest_size|status" > "$OUTPUT_FILE"

tail -n +2 "$INPUT_FILE" | while IFS='|' read -r docinfoid document doctype urltype urlname extra
do
  docinfoid=$(printf '%s' "$docinfoid" | tr -d '"\r')
  urltype=$(printf '%s' "$urltype" | tr -d '"\r')
  urlname=$(printf '%s' "$urlname" | tr -d '"\r')

  if [ "$urltype" != "FILE" ]; then
    continue
  fi

  case "$urlname" in
    /doclinks/*)
      relative_path="${urlname#/doclinks/}"
      ;;
    *)
      echo "$docinfoid|$urlname|||||||skipped_bad_path" >> "$OUTPUT_FILE"
      continue
      ;;
  esac

  source_path="$SOURCE_ROOT/$relative_path"
  dest_path="$DEST_ROOT/$relative_path"

  source_exists="false"
  dest_exists="false"
  source_size=""
  dest_size=""
  status="ready"

  if [ -f "$source_path" ]; then
    source_exists="true"
    source_size=$(stat -c%s "$source_path")
  else
    status="source_missing"
  fi

  if [ -f "$dest_path" ]; then
    dest_exists="true"
    dest_size=$(stat -c%s "$dest_path")

    if [ "$source_size" = "$dest_size" ] && [ -n "$source_size" ]; then
      status="dest_exists_same_size"
    else
      status="dest_exists_different_size"
    fi
  fi

  echo "$docinfoid|$urlname|$source_path|$dest_path|$source_exists|$dest_exists|$source_size|$dest_size|$status" >> "$OUTPUT_FILE"
done

echo "Manifest created: $OUTPUT_FILE"
