"""Make Instagram Reel thumbnails (1080x1920) from a video, and optionally upload with instagrapi.

Usage:
  python thumbnail.py video.mp4                  # 5 candidate thumbnails into ./thumbnails
  python thumbnail.py video.mp4 -n 3 -o out      # 3 thumbnails into ./out
  python thumbnail.py video.mp4 --upload thumbnails/thumb_1.jpg --caption "Hi"
    (upload needs IG_USERNAME and IG_PASSWORD environment variables)
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

REEL_FILTER = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"


def duration(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def make_thumbnails(video, count=5, out_dir="thumbnails"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    length = duration(video)
    paths = []
    for i in range(count):
        t = length * (i + 1) / (count + 1)
        path = out / f"thumb_{i + 1}.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", video,
             "-frames:v", "1", "-vf", REEL_FILTER, "-q:v", "2", str(path)],
            check=True,
        )
        paths.append(path)
    return paths


def upload(video, thumb, caption):
    from instagrapi import Client

    cl = Client()
    cl.login(os.environ["IG_USERNAME"], os.environ["IG_PASSWORD"])
    media = cl.clip_upload(Path(video), caption, thumbnail=Path(thumb))
    return media.pk


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("-n", "--count", type=int, default=5)
    p.add_argument("-o", "--out", default="thumbnails")
    p.add_argument("--upload", metavar="THUMB")
    p.add_argument("--caption", default="")
    a = p.parse_args()

    if a.upload:
        print("Uploaded media id:", upload(a.video, a.upload, a.caption))
    else:
        for path in make_thumbnails(a.video, a.count, a.out):
            print(path)
