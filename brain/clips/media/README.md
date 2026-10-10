# Clip media

One file per room: `dining.mp4` (Kainan), `stairs.mp4` (Hagdan), `balcony.mp4` (Balkonahe). `.mov`, `.MOV`, and `.webm` with the same English stem count too, and so does the Tagalog id (`kainan.mp4`). The filename stem is English; the room id is Tagalog.

The three demo `.mp4` files above are in the clone. Any other file in this folder stays on the hub and is gitignored.

iPhone `.mov` files are often HEVC, which pip OpenCV cannot decode. Convert a folder with `brain/clips/convert.sh`:

```bash
ffmpeg -i in.mov -c:v libx264 -an out.mp4
```
