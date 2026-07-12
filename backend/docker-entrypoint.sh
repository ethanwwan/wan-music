#!/bin/bash
set -e

if [ "$(id -u)" = "0" ]; then
    chown -R wanmusic:wanmusic /app/cookie /app/logs 2>/dev/null || true
    if command -v gosu &>/dev/null; then
        exec gosu wanmusic "$@"
    fi
    >&2 echo "WARNING: gosu not found, falling back to su (signal forwarding may be degraded)"
    exec su -s /bin/sh -c 'exec "$@"' wanmusic -- "$@"
fi

exec "$@"
