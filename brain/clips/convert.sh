#!/bin/sh
# iPhone .mov is often HEVC. pip OpenCV decodes H.264.
set -eu
dir=${1:?usage: brain/clips/convert.sh folder}
for input in "$dir"/*; do
  [ -f "$input" ] || continue
  name=$(basename "$input")
  case $name in
    *.mp4|*.mov|*.webm|*.MP4|*.MOV|*.WEBM) ;;
    *) continue ;;
  esac
  stem=${name%.*}
  output="$dir/$stem.mp4"
  if [ "$input" = "$output" ]; then
    output="$dir/$stem.h264.mp4"
  fi
  ffmpeg -i "$input" -c:v libx264 -an "$output"
done
