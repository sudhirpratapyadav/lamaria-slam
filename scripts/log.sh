#!/usr/bin/env bash
# Append a timestamped decision line to track_logs_v1/logs.md using the real clock.
# Usage: scripts/log.sh "text"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
printf -- "- **%s** %s\n" "$(date '+%Y-%m-%d %H:%M')" "$1" >> "$ROOT/track_logs_v1/logs.md"
