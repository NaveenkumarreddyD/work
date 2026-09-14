#!/usr/bin/env bash
set -u

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "Usage: $0 <manifest_file> <log_file> [dry-run|execute]"
  exit 1
fi

MANIFEST_FILE="$1"
LOG_FILE="$2"
MODE="${3:-dry-run}"

if [ "$MODE" != "dry-run" ] && [ "$MODE" != "execute" ]; then
  echo "Mode must be dry-run or execute"
  exit 1
fi

echo "docinfoid|source_path|dest_path|action" > "$LOG_FILE"

tail -n +2 "$MANIFEST_FILE" | while IFS='|' read -r docinfoid urlname source_path dest_path source_exists dest_exists source_size dest_size status
do
  if [ "$status" = "source_missing" ]; then
    echo "$docinfoid|$source_path|$dest_path|SOURCE_MISSING" >> "$LOG_FILE"
    continue
  fi

  if [ "$status" = "dest_exists_same_size" ]; then
    echo "$docinfoid|$source_path|$dest_path|SKIPPED_ALREADY_EXISTS" >> "$LOG_FILE"
    continue
  fi

  if [ "$status" = "dest_exists_different_size" ]; then
    echo "$docinfoid|$source_path|$dest_path|SKIPPED_DEST_DIFFERENT_SIZE" >> "$LOG_FILE"
    continue
  fi

  if [ "$MODE" = "dry-run" ]; then
    echo "$docinfoid|$source_path|$dest_path|DRY_RUN_READY" >> "$LOG_FILE"
    continue
  fi

  mkdir -p "$(dirname "$dest_path")"
  cp -p "$source_path" "$dest_path"

  if [ "$?" -eq 0 ]; then
    echo "$docinfoid|$source_path|$dest_path|COPIED" >> "$LOG_FILE"
  else
    echo "$docinfoid|$source_path|$dest_path|COPY_FAILED" >> "$LOG_FILE"
  fi
done

echo "Done. Log created: $LOG_FILE"
