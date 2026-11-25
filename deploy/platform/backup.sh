#!/usr/bin/env bash
# Daily backup of the live database. Installed by cron on the server:
#   /etc/cron.d/danadial-backup
#
# A backup that cannot be read is not kept, and old backups are removed only
# after a new one is good. So a failure never leaves the server with fewer
# good backups than before.
set -euo pipefail

DIR=/opt/backups/daily
KEEP_DAYS=14
COMPOSE_DIR=/opt/dograh/deploy/platform

mkdir -p "$DIR"
chmod 700 /opt/backups "$DIR"
cd "$COMPOSE_DIR"

name="danadial-$(date -u +%Y%m%d-%H%M).dump"
new="$DIR/.$name.part"
trap 'rm -f "$new"' EXIT

docker compose exec -T postgres pg_dump -U postgres -d postgres -Fc > "$new"
# The archive must have a table of contents with the users table in it.
contents=$(docker compose exec -T postgres pg_restore --list < "$new")
grep -q "TABLE DATA public users " <<< "$contents" || {
  echo "$(date -u +%FT%TZ) the new backup has no users table" >&2
  exit 1
}

chmod 600 "$new"
mv "$new" "$DIR/$name"
find "$DIR" -name 'danadial-*.dump' -mtime +"$KEEP_DAYS" -delete
echo "$(date -u +%FT%TZ) ok $name $(stat -c %s "$DIR/$name") bytes, $(ls "$DIR" | wc -l) kept"
