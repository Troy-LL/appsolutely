# Clip media

One file per room: `hagdan.mp4`, `sala.mp4`, `balkonahe.mp4`, and the same for `.mov` and `.webm`. The room id is the filename. Footage stays on the hub and is gitignored.

iPhone `.mov` files are often HEVC, which pip OpenCV cannot decode. Convert a folder with `brain/clips/convert.sh`:

```bash
ffmpeg -i in.mov -c:v libx264 -an out.mp4
```
