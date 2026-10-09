# Face gallery

One folder per person: `troy/`, `joy/`, `donita/`. Each folder holds 1 to 5 `.jpg` or `.png` photos. The photos stay on the hub. Files in this folder, other than this README, are gitignored.

```bash
python3 -m brain.face enroll troy --webcam
python3 -m brain.face enroll joy --photo joy.jpg
```

`--webcam` saves three cropped faces, one second apart. `--photo` copies a picture in. `watch` and identify keep frames in memory and do not write them.
