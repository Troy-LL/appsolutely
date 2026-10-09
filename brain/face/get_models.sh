#!/bin/sh
# One online run. Saves OpenCV Zoo YuNet and SFace into brain/face/models/.
set -eu
cd "$(dirname "$0")"
mkdir -p models

fetch() {
  name="$1"
  primary="$2"
  fallback="$3"
  dest="models/$name"
  if [ -f "$dest" ]; then
    size=$(wc -c < "$dest" | tr -d ' ')
    if [ "$size" -ge 100000 ]; then
      echo "have $dest"
      return 0
    fi
    rm -f "$dest"
  fi
  for url in "$primary" "$fallback"; do
    echo "get $name"
    rm -f "$dest.part"
    if curl -fL --retry 3 --retry-delay 2 -o "$dest.part" "$url"; then
      sig=$(LC_ALL=C head -c 200 "$dest.part" || true)
      case "$sig" in
        *git-lfs*)
          rm -f "$dest.part"
          continue
          ;;
      esac
      size=$(wc -c < "$dest.part" | tr -d ' ')
      if [ "$size" -ge 100000 ]; then
        mv "$dest.part" "$dest"
        echo "saved $dest ($size bytes)"
        return 0
      fi
    fi
    rm -f "$dest.part"
  done
  echo "could not download $name" >&2
  exit 1
}

fetch face_detection_yunet_2023mar.onnx \
  "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" \
  "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

fetch face_recognition_sface_2021dec.onnx \
  "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" \
  "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
