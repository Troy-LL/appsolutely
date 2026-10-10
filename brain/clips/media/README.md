# Clip media

One file per room: `stairs.MOV` (Hagdan), `dining.MOV` (Kainan), `balcony.MOV` (Balkonahe). `.mp4` and `.webm` with the same stem count too. The filename is the English stem; the room id is Tagalog. Footage stays on the hub and is gitignored.

iPhone `.mov` files are often HEVC, which pip OpenCV cannot decode. Convert a folder with `brain/clips/convert.sh`:

```bash
ffmpeg -i in.mov -c:v libx264 -an out.mp4
```
