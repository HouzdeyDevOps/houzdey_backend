"""Smoke-test the R2 media pipeline against the real bucket.

Run from the backend folder (uses the R2_* values in .env):

    python scripts/check_r2_upload.py                      # image only
    python scripts/check_r2_upload.py --video some.mp4     # image + video

It uploads a generated image (and optionally a video) through the same code the API
uses, downloads each public URL to confirm it is served, then deletes the test files.
"""
import argparse
import asyncio
import io
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Only the R2 settings matter here; fill the app's other required settings so Settings() loads
# even when .env contains just the R2 values.
for _name in (
    "SECRET_KEY", "MONGO_URL", "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET",
    "CLOUDINARY_URL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI",
    "BREVO_SMTP_USERNAME", "BREVO_SMTP_PASSWORD", "EMAIL_FROM", "TERMII_API_KEY",
):
    os.environ.setdefault(_name, "unused")

from PIL import Image, ImageDraw  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.utils import storage  # noqa: E402

FOLDER = "_healthcheck"
failures = []


def check(ok: bool, message: str) -> bool:
    print(f"  [{'ok' if ok else 'FAIL'}] {message}")
    if not ok:
        failures.append(message)
    return ok


def fetch(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "houzdey-r2-check"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except urllib.error.HTTPError as e:
        return e.code, "", b""
    except urllib.error.URLError as e:
        print(f"      request failed: {e.reason}")
        return 0, "", b""


def sample_image() -> bytes:
    image = Image.new("RGB", (1600, 1000), (30, 30, 30))
    draw = ImageDraw.Draw(image)
    for i in range(0, 1600, 40):
        draw.rectangle((i, 0, i + 20, 1000), fill=(60 + i // 10, 90, 140))
    out = io.BytesIO()
    image.save(out, format="JPEG")
    return out.getvalue()


async def run(video_path):
    print("Config")
    check(storage.r2_enabled(), "R2_ACCOUNT_ID / ACCESS_KEY_ID / SECRET_ACCESS_KEY / BUCKET / PUBLIC_URL are all set")
    if not storage.r2_enabled():
        return
    print(f"  bucket={settings.R2_BUCKET}  public url={settings.R2_PUBLIC_URL}")
    check("yourdomain" not in settings.R2_PUBLIC_URL, "R2_PUBLIC_URL is not the placeholder")
    check(
        "r2.cloudflarestorage.com" not in settings.R2_PUBLIC_URL,
        "R2_PUBLIC_URL is a public address (r2.dev or a custom domain), not the private S3 API endpoint",
    )
    check(storage._logo() is not None, "watermark logo found")
    ffmpeg = shutil.which(settings.FFMPEG_PATH) and shutil.which(settings.FFPROBE_PATH)
    print(f"  ffmpeg/ffprobe: {'found' if ffmpeg else 'NOT found (videos will be stored without a watermark)'}")

    uploaded = []

    print("Image")
    try:
        url = await storage.upload_image(sample_image(), FOLDER)
    except Exception as e:
        check(False, f"upload failed: {type(e).__name__}: {e}")
        return
    uploaded.append(url)
    check(url.endswith(".webp"), f"uploaded -> {url}")
    status, content_type, body = fetch(url)
    check(status == 200, f"public URL returns 200 (got {status})")
    if status == 200:
        check(content_type.startswith("image/webp"), f"content type is image/webp (got {content_type})")
        check(Image.open(io.BytesIO(body)).size == (1600, 1000), "image decodes at the expected size")

    if video_path:
        print("Video")
        try:
            url = await storage.upload_video(Path(video_path).read_bytes(), FOLDER)
        except Exception as e:
            check(False, f"upload failed: {type(e).__name__}: {e}")
        else:
            uploaded.append(url)
            print(f"  uploaded -> {url}")
            status, content_type, body = fetch(url)
            check(status == 200, f"public URL returns 200 (got {status})")
            check(content_type.startswith("video/"), f"content type is video/* (got {content_type})")

    print("Cleanup")
    for url in uploaded:
        check(await storage.delete_media(url), f"deleted {url}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", help="optional video file to upload as well")
    args = parser.parse_args()
    asyncio.run(run(args.video))
    print("\nFAILED" if failures else "\nAll checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
