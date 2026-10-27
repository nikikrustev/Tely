#!/usr/bin/env bash
# Optional finishing step for the demo video (file 42 "Video assembly").
# Takes the Clipchamp export (no captions burned in yet) and adds, for a muted viewer:
#   - the SDH captions from video/captions_sdh.srt, burned in;
#   - a left/right level meter (showvolume) top-left, so stereo position shows without sound;
#   - a two-channel waveform strip along the bottom (showwaves, split_channels).
# Then checks the length is under 1:55 (file 14).
# Works with an LGPL ffmpeg build: every filter below (asplit, showwaves, showvolume, overlay, subtitles via libass)
# and the AAC encoder are LGPL-compatible, and the H.264 encoder is picked from LGPL-safe ones (OpenH264, or the
# GPU/OS encoders). libx264 is GPL, so it is never used. The script checks each filter and the encoder before it runs.
# Usage, from anywhere:  bash video/assemble.sh [edit.mp4] [out.mp4]
#   defaults: out/video/edit.mp4 -> out/video/tely_demo.mp4 (out/ is git-ignored)
#   ENCODER=h264_nvenc bash video/assemble.sh   to force an encoder
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"   # the subtitles filter gets a relative path: a Windows drive colon would break the filter graph
IN="${1:-out/video/edit.mp4}"
OUT="${2:-out/video/tely_demo.mp4}"
SRT="video/captions_sdh.srt"
MAX_S=115

command -v ffmpeg >/dev/null || { echo "ffmpeg not found on PATH (an LGPL build is enough)"; exit 2; }
command -v ffprobe >/dev/null || { echo "ffprobe not found on PATH (it ships with ffmpeg)"; exit 2; }
[ -f "$IN" ] || { echo "no input video: $IN (export the edit from Clipchamp first)"; exit 2; }
[ -f "$SRT" ] || { echo "no $SRT: run python video/make_captions.py"; exit 2; }
if ffmpeg -hide_banner -version | grep -q -- '--enable-gpl'; then
  echo "note: this ffmpeg build is GPL; the script still avoids libx264, so an LGPL build gives the same result"
fi

filters="$(ffmpeg -hide_banner -filters 2>/dev/null)"
for f in asplit showwaves showvolume overlay subtitles; do
  grep -qE "^ [.A-Z|]+ +$f +" <<<"$filters" || { echo "this ffmpeg has no '$f' filter (subtitles needs libass)"; exit 2; }
done

encoders="$(ffmpeg -hide_banner -encoders 2>/dev/null)"
has_enc() { grep -qE "^ V[.A-Z]+ +$1 " <<<"$encoders"; }
if [ -n "${ENCODER:-}" ]; then
  [ "$ENCODER" != "libx264" ] || { echo "libx264 is GPL; pick an LGPL-safe encoder"; exit 2; }
  has_enc "$ENCODER" || { echo "this ffmpeg has no '$ENCODER' encoder"; exit 2; }
  VENC="$ENCODER"
else
  VENC=""
  for e in libopenh264 h264_nvenc h264_amf h264_qsv h264_mf h264_videotoolbox; do
    if has_enc "$e"; then VENC="$e"; break; fi
  done
  [ -n "$VENC" ] || { echo "no LGPL-safe H.264 encoder found (tried OpenH264, NVENC, AMF, QSV, Media Foundation, VideoToolbox)"; exit 2; }
fi
echo "encoder: $VENC"

mkdir -p "$(dirname "$OUT")"
# Video stays at the edit's size; the strip and meter are drawn for 1920x1080 (file 14: record at 1080p).
ffmpeg -hide_banner -y -i "$IN" -filter_complex \
"[0:a]asplit=2[a1][a2];\
[a1]showwaves=s=1920x120:mode=cline:split_channels=1:colors=white|cyan[w];\
[a2]showvolume=w=400:h=20:o=h[m];\
[0:v][w]overlay=0:H-h-60[v1];\
[v1][m]overlay=40:40,\
subtitles=$SRT:force_style='FontSize=26,BorderStyle=3,Outline=0,BackColour=&H80000000'[v]" \
  -map "[v]" -map 0:a -c:v "$VENC" -b:v 8M -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart -shortest "$OUT"

dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")"
echo "wrote $OUT: ${dur} s"
awk -v d="$dur" -v m="$MAX_S" 'BEGIN { if (d + 0 > m) { print "TOO LONG: over " m " s (1:55); trim the edit"; exit 1 } }'
