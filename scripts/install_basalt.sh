#!/usr/bin/env bash
# Copy the built basalt_vio and libbasalt.so into third_party/basalt/install atomically (temp + mv),
# (from build/dev by default; build/release is frozen for batches that still point at it) so a rebuild never races a run that is just starting (ld rewrites the output in place and a
# process launched in that window gets "Permission denied"). Batches point BASALT_VIO here.
set -e
cd "$(dirname "$0")/.."
B=${1:-third_party/basalt/build/dev}; I=third_party/basalt/install
for f in basalt_vio libbasalt.so; do cp "$B/$f" "$I/.$f.tmp" && mv -f "$I/.$f.tmp" "$I/$f"; done
echo "installed $(date -Is): $(ls -la $I/basalt_vio | awk '{print $6,$7,$8}')"
