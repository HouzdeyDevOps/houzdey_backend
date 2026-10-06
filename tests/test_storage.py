import asyncio
import io
import shutil
import subprocess

import pytest
from fastapi import HTTPException
from PIL import Image

from app.core.config import settings
from app.utils import storage


@pytest.fixture
def r2(monkeypatch):
    for name, value in {
        "R2_ACCOUNT_ID": "acct", "R2_ACCESS_KEY_ID": "key", "R2_SECRET_ACCESS_KEY": "secret",
        "R2_BUCKET": "bucket", "R2_PUBLIC_URL": "https://media.example.com/",
    }.items():
        monkeypatch.setattr(settings, name, value)
    puts, deletes = [], []

    class FakeClient:
        def put_object(self, **kwargs):
            puts.append(kwargs)

        def delete_object(self, **kwargs):
            deletes.append(kwargs)

    monkeypatch.setattr(storage, "_client", lambda: FakeClient())
    return puts, deletes


def _png(size=(1200, 800), colour=(0, 0, 0), mode="RGB"):
    out = io.BytesIO()
    Image.new(mode, size, colour).save(out, format="PNG")
    return out.getvalue()


def test_image_is_converted_to_webp_and_watermarked(r2):
    puts, _ = r2
    url = asyncio.run(storage.upload_image(_png(), "properties"))
    assert url.startswith("https://media.example.com/properties/") and url.endswith(".webp")
    put = puts[0]
    assert put["Bucket"] == "bucket" and put["ContentType"] == "image/webp"
    stored = Image.open(io.BytesIO(put["Body"])).convert("RGB")
    assert stored.size == (1200, 800)
    # A black image must have light watermark pixels bottom-right and stay black top-left.
    assert max(stored.getpixel((1150, 770))) > 100
    assert max(stored.getpixel((10, 10))) < 20


def test_profile_picture_is_not_watermarked_and_is_resized(r2):
    puts, _ = r2
    asyncio.run(storage.upload_image(_png((2400, 1600)), "profile_pictures", watermark=False, max_side=800))
    stored = Image.open(io.BytesIO(puts[0]["Body"])).convert("RGB")
    assert max(stored.size) == 800
    assert max(stored.getpixel((stored.width - 20, stored.height - 20))) < 20


def test_transparent_png_is_flattened_onto_white(r2):
    puts, _ = r2
    asyncio.run(storage.upload_image(_png((600, 400), (0, 0, 0, 0), "RGBA"), "properties", watermark=False))
    stored = Image.open(io.BytesIO(puts[0]["Body"])).convert("RGB")
    assert min(stored.getpixel((5, 5))) > 240


@pytest.mark.parametrize("payload", [b"<script>alert(1)</script>", b"%PDF-1.4 fake", b"", b"GIF89a" + b"\x00" * 4])
def test_non_images_are_rejected(r2, payload):
    puts, _ = r2
    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.upload_image(payload, "properties"))
    assert exc.value.status_code == 400
    assert puts == []


def test_oversized_image_is_rejected(r2, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 1000)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.upload_image(_png(), "properties"))
    assert exc.value.status_code == 400


def test_non_video_is_rejected(r2):
    puts, _ = r2
    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.upload_video(b"not a video at all, just text", "properties"))
    assert exc.value.status_code == 400
    assert puts == []


def test_video_falls_back_to_original_when_ffmpeg_missing(r2, monkeypatch):
    puts, _ = r2
    monkeypatch.setattr(settings, "FFMPEG_PATH", "ffmpeg-does-not-exist")
    monkeypatch.setattr(settings, "FFPROBE_PATH", "ffprobe-does-not-exist")
    fake_mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
    url = asyncio.run(storage.upload_video(fake_mp4, "properties"))
    assert url.endswith(".mp4") and "/properties/videos/" in url
    assert puts[0]["Body"] == fake_mp4 and puts[0]["ContentType"] == "video/mp4"


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg not installed")
def test_video_is_watermarked_with_ffmpeg(r2, tmp_path):
    puts, _ = r2
    src = tmp_path / "in.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:d=1", "-pix_fmt", "yuv420p", str(src)],
        capture_output=True, check=True,
    )
    asyncio.run(storage.upload_video(src.read_bytes(), "properties"))
    out = tmp_path / "out.mp4"
    out.write_bytes(puts[0]["Body"])
    frame = tmp_path / "frame.png"
    subprocess.run(["ffmpeg", "-y", "-i", str(out), "-frames:v", "1", str(frame)], capture_output=True, check=True)
    img = Image.open(frame).convert("RGB")
    assert max(img.getpixel((img.width - 30, img.height - 25))) > 100
    assert max(img.getpixel((10, 10))) < 30


def test_delete_media_routes_by_url(r2, monkeypatch):
    _, deletes = r2
    assert asyncio.run(storage.delete_media("https://media.example.com/properties/abc.webp")) is True
    assert deletes == [{"Bucket": "bucket", "Key": "properties/abc.webp"}]
    assert asyncio.run(storage.delete_media("https://lh3.googleusercontent.com/photo.jpg")) is False
    assert asyncio.run(storage.delete_media("")) is False

    called = []

    async def fake_destroy(public_id):
        called.append(public_id)
        return True

    monkeypatch.setattr(storage.cloudinary_config, "delete_image_from_cloudinary", fake_destroy)
    url = "https://res.cloudinary.com/x/image/upload/v1/houzdey/properties/pic.jpg"
    assert asyncio.run(storage.delete_media(url)) is True
    assert called == ["houzdey/properties/pic"]


def test_falls_back_to_cloudinary_when_r2_unset(monkeypatch):
    monkeypatch.setattr(settings, "R2_BUCKET", "")

    async def fake_upload(contents, folder):
        return "https://res.cloudinary.com/x/pic.jpg"

    monkeypatch.setattr(storage.cloudinary_config, "upload_image_to_cloudinary", fake_upload)
    assert asyncio.run(storage.upload_image(_png(), "properties")) == "https://res.cloudinary.com/x/pic.jpg"


def test_video_upload_with_background_tasks_returns_url_before_processing(r2):
    from fastapi import BackgroundTasks

    puts, _ = r2
    tasks = BackgroundTasks()
    fake_mp4 = b"\x00\x00\x00ftypmp42" + b"\x00" * 64
    url = asyncio.run(storage.upload_video(fake_mp4, "properties", tasks))
    assert url.endswith(".mp4") and "/properties/videos/" in url
    assert puts == []  # nothing stored until the background task runs
    asyncio.run(tasks())
    assert len(puts) == 1 and puts[0]["Key"] == url.split(".example.com/")[1]
