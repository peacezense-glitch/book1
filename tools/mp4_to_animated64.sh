#!/usr/bin/env bash
# Convert a key animation MP4 into PNG frames, a 64-frame sequence, APNG, and an 8x8 spritesheet.
set -euo pipefail

SRC="${1:-}"
NAME="${2:-$(basename "${SRC%.*}")}"
if [[ -z "$SRC" || ! -f "$SRC" ]]; then
  echo "usage: $0 <input.mp4> [name]" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/assets/${NAME}"
mkdir -p "$OUT/frames" "$OUT/animated64"

DURATION="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$SRC")"
FPS64="$(python3 -c "print(64.0 / float('${DURATION}'))")"

ffmpeg -y -i "$SRC" -fps_mode passthrough "$OUT/frames/${NAME}_%02d.png"
ffmpeg -y -i "$SRC" -vf "fps=${FPS64}" -frames:v 64 "$OUT/animated64/animated64_%02d.png"
ffmpeg -y -framerate 25 -i "$OUT/frames/${NAME}_%02d.png" -plays 0 -f apng "$OUT/${NAME}.png"
ffmpeg -y -framerate "$FPS64" -i "$OUT/animated64/animated64_%02d.png" -plays 0 -f apng "$OUT/animated64.png"
ffmpeg -y -i "$OUT/animated64/animated64_%02d.png" -filter_complex "tile=8x8" -frames:v 1 -update 1 "$OUT/animated64_spritesheet.png"

echo "wrote $OUT (duration=${DURATION}s fps64=${FPS64})"
