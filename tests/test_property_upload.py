import io
import json

from PIL import Image

import app.api.routes.properties as properties_routes
from tests.test_auth import API, login


def _png():
    out = io.BytesIO()
    Image.new("RGB", (40, 40), (200, 10, 10)).save(out, format="PNG")
    return out.getvalue()


def _form():
    return {
        "title": "2 Bedroom Flat", "type": "Apartment", "price": "500000", "description": "Nice flat",
        "amenities": json.dumps([{"name": "Running water", "icon": ""}]), "condition": "Good",
        "furnishing": "Unfurnished", "address": "Trans-Ekulu, Enugu", "state": "Enugu", "lga": "Enugu East",
    }


def test_create_property_uploads_images_and_video(client, make_user, monkeypatch):
    calls = []

    async def fake_image(contents, folder, **kwargs):
        calls.append(("image", folder))
        return f"https://media.example.com/{folder}/img{len(calls)}.webp"

    async def fake_video(contents, folder):
        calls.append(("video", folder))
        return f"https://media.example.com/{folder}/videos/clip.mp4"

    monkeypatch.setattr(properties_routes, "upload_image", fake_image)
    monkeypatch.setattr(properties_routes, "upload_video", fake_video)
    make_user()
    token = login(client).json()["access_token"]

    files = [("images", ("a.png", _png(), "image/png")), ("images", ("b.png", _png(), "image/png")),
             ("video", ("c.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 32, "video/mp4"))]
    r = client.post(f"{API}/properties", data=_form(), files=files, headers={"Authorization": f"Bearer {token}"})

    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert len(body["images"]) == 2 and all(u.endswith(".webp") for u in body["images"])
    assert body["video"] == "https://media.example.com/properties/videos/clip.mp4"
    assert sorted(calls) == [("image", "properties"), ("image", "properties"), ("video", "properties")]


def test_create_property_without_video(client, make_user, monkeypatch):
    async def fake_image(contents, folder, **kwargs):
        return "https://media.example.com/properties/img.webp"

    monkeypatch.setattr(properties_routes, "upload_image", fake_image)
    make_user()
    token = login(client).json()["access_token"]
    r = client.post(f"{API}/properties", data=_form(), files=[("images", ("a.png", _png(), "image/png"))],
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (200, 201), r.text
    assert r.json()["video"] is None
