"""Media storage on Cloudflare R2 (S3 API) with a Houzdey watermark.

Images are validated and re-encoded with Pillow; videos are validated by magic bytes and
re-encoded with ffmpeg. If R2 is not configured the helpers fall back to Cloudinary.
"""
import asyncio
import io
import logging
import subprocess
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config
from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageOps

from app.core.config import settings
from app.utils import cloudinary_config

logger = logging.getLogger(__name__)

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "houzdey-logo.png"
ALLOWED_IMAGE_FORMATS = ["JPEG", "PNG", "WEBP", "GIF"]
MAX_IMAGE_PIXELS = 50_000_000
MAX_VIDEO_WIDTH = 1280
FFMPEG_TIMEOUT_SECONDS = 300
CACHE_CONTROL = "public, max-age=31536000, immutable"

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def r2_enabled() -> bool:
    return all([
        settings.R2_ACCOUNT_ID, settings.R2_ACCESS_KEY_ID, settings.R2_SECRET_ACCESS_KEY,
        settings.R2_BUCKET, settings.R2_PUBLIC_URL,
    ])


@lru_cache(maxsize=1)
def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def _public_url(key: str) -> str:
    return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{key}"


def _put(key: str, body: bytes, content_type: str) -> None:
    _client().put_object(
        Bucket=settings.R2_BUCKET, Key=key, Body=body,
        ContentType=content_type, CacheControl=CACHE_CONTROL,
    )


@lru_cache(maxsize=1)
def _logo() -> Optional[Image.Image]:
    """The logo cropped to its visible pixels, or None if the file is missing."""
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
    except OSError:
        logger.warning("Watermark logo not found at %s; uploads will not be watermarked", LOGO_PATH)
        return None
    bbox = logo.getchannel("A").getbbox()
    return logo.crop(bbox) if bbox else logo


def _watermark_plate(width: int) -> Optional[Image.Image]:
    """The logo on a translucent white rounded plate, `width` pixels wide, readable on any photo."""
    logo = _logo()
    if logo is None or width < 40:
        return None
    pad = max(4, round(width * 0.08))
    inner_w = width - 2 * pad
    inner_h = round(logo.height * inner_w / logo.width)
    plate = Image.new("RGBA", (width, inner_h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle(
        (0, 0, plate.width - 1, plate.height - 1), radius=pad * 1.5, fill=(255, 255, 255, 190)
    )
    plate.alpha_composite(logo.resize((inner_w, inner_h), Image.LANCZOS), (pad, pad))
    return plate


def _process_image(contents: bytes, watermark: bool, max_side: int) -> bytes:
    try:
        image = Image.open(io.BytesIO(contents), formats=ALLOWED_IMAGE_FORMATS)
        image = ImageOps.exif_transpose(image)
        if image.mode in ("RGBA", "LA", "P"):
            rgba = image.convert("RGBA")
            image = Image.new("RGB", rgba.size, (255, 255, 255))
            image.paste(rgba, mask=rgba.getchannel("A"))
        else:
            image = image.convert("RGB")
    except (OSError, ValueError, Image.DecompressionBombError) as e:
        logger.info("Rejected image upload: %s", e)
        raise HTTPException(status_code=400, detail="File is not a supported image (JPEG, PNG, WebP or GIF)")

    image.thumbnail((max_side, max_side), Image.LANCZOS)

    if watermark and settings.WATERMARK_ENABLED:
        plate = _watermark_plate(round(image.width * 0.22))
        if plate is not None:
            margin = round(image.width * 0.02)
            canvas = image.convert("RGBA")
            canvas.alpha_composite(plate, (image.width - plate.width - margin, image.height - plate.height - margin))
            image = canvas.convert("RGB")

    out = io.BytesIO()
    image.save(out, format="WEBP", quality=82, method=4)
    return out.getvalue()


def _is_video(header: bytes) -> bool:
    # MP4 / MOV have "ftyp" at offset 4; WebM / MKV start with the EBML magic.
    return header[4:8] == b"ftyp" or header.startswith(b"\x1aE\xdf\xa3")


def _probe_width(path: str) -> int:
    result = subprocess.run(
        [settings.FFPROBE_PATH, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=30, check=True,
    )
    return int(result.stdout.strip().split(",")[0])


def _process_video(contents: bytes) -> Optional[bytes]:
    """Re-encode to a 720p-ish H.264 MP4 with the watermark. Returns None if ffmpeg is unavailable or fails."""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src, dst, plate_path = f"{tmp}/in", f"{tmp}/out.mp4", f"{tmp}/plate.png"
            Path(src).write_bytes(contents)
            out_width = min(_probe_width(src), MAX_VIDEO_WIDTH)
            plate = _watermark_plate(round(out_width * 0.2))
            if plate is None:
                return None
            plate.save(plate_path)
            margin = round(out_width * 0.02)
            subprocess.run(
                [settings.FFMPEG_PATH, "-y", "-i", src, "-i", plate_path, "-filter_complex",
                 f"[0:v]scale='min({MAX_VIDEO_WIDTH},iw)':-2[v];[v][1:v]overlay=W-w-{margin}:H-h-{margin}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", dst],
                capture_output=True, timeout=FFMPEG_TIMEOUT_SECONDS, check=True,
            )
            return Path(dst).read_bytes()
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        logger.warning("Video watermarking failed, storing the original: %s", e)
        return None


async def upload_image(contents: bytes, folder: str, *, watermark: bool = True, max_side: int = 2000) -> str:
    """Validate, resize, watermark and store an image; returns its public URL."""
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"Image exceeds the {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB size limit")
    if not r2_enabled():
        return await cloudinary_config.upload_image_to_cloudinary(contents, folder)

    data = await asyncio.to_thread(_process_image, contents, watermark, max_side)
    key = f"{folder}/{uuid.uuid4().hex}.webp"
    await asyncio.to_thread(_put, key, data, "image/webp")
    return _public_url(key)


async def upload_video(contents: bytes, folder: str) -> str:
    """Validate, watermark and store a video; returns its public URL."""
    if len(contents) > settings.MAX_VIDEO_SIZE:
        raise HTTPException(status_code=400, detail=f"Video exceeds the {settings.MAX_VIDEO_SIZE // (1024 * 1024)}MB size limit")
    if not _is_video(contents[:12]):
        raise HTTPException(status_code=400, detail="File is not a supported video (MP4, MOV or WebM)")
    if not r2_enabled():
        return await cloudinary_config.upload_video_to_cloudinary(contents, folder)

    data = await asyncio.to_thread(_process_video, contents) if settings.WATERMARK_ENABLED else None
    if data is None:
        data = contents
        content_type = "video/webm" if contents.startswith(b"\x1aE\xdf\xa3") else "video/mp4"
        ext = "webm" if content_type == "video/webm" else "mp4"
    else:
        content_type, ext = "video/mp4", "mp4"
    key = f"{folder}/videos/{uuid.uuid4().hex}.{ext}"
    await asyncio.to_thread(_put, key, data, content_type)
    return _public_url(key)


async def delete_media(url: str) -> bool:
    """Delete a stored file by its public URL (R2 or legacy Cloudinary). Returns True if deleted."""
    if not url:
        return False
    if r2_enabled() and url.startswith(settings.R2_PUBLIC_URL.rstrip("/") + "/"):
        key = url[len(settings.R2_PUBLIC_URL.rstrip("/")) + 1:]
        try:
            await asyncio.to_thread(_client().delete_object, Bucket=settings.R2_BUCKET, Key=key)
            return True
        except Exception as e:
            logger.warning("Failed to delete %s from R2: %s", key, e)
            return False
    if "res.cloudinary.com" in url:
        public_id = cloudinary_config.extract_public_id_from_url(url)
        return await cloudinary_config.delete_image_from_cloudinary(public_id)
    return False
