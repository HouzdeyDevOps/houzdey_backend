import time

from fastapi.testclient import TestClient

from main import app
from tests.conftest import PASSWORD

API = "/api/v1"


def login(client, email="user@example.com"):
    r = client.post(f"{API}/users/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r


def fresh_client_with(access=None, refresh=None, headers=None):
    c = TestClient(app, headers=headers or {})
    if access:
        c.cookies.set("access_token", access)
    if refresh:
        c.cookies.set("refresh_token", refresh)
    return c


def test_login_sets_httponly_cookies(client, make_user):
    make_user()
    r = login(client)
    cookies = r.headers.get_list("set-cookie")
    assert any(c.startswith("access_token=") and "HttpOnly" in c for c in cookies)
    assert any(c.startswith("refresh_token=") and "HttpOnly" in c for c in cookies)


def test_cookie_only_and_header_only_both_authenticate(client, make_user):
    make_user()
    body = login(client).json()
    assert fresh_client_with(access=body["access_token"]).get(f"{API}/users/me").status_code == 200
    header_only = fresh_client_with(headers={"Authorization": f"Bearer {body['access_token']}"})
    assert header_only.get(f"{API}/users/me").status_code == 200
    assert fresh_client_with().get(f"{API}/users/me").status_code == 401


def test_logout_revokes_access_and_refresh_tokens(client, make_user):
    make_user()
    body = login(client).json()
    access, refresh = body["access_token"], body["refresh_token"]
    c = fresh_client_with(access=access, refresh=refresh)
    assert c.post(f"{API}/users/logout").status_code == 200
    assert fresh_client_with(access=access).get(f"{API}/users/me").status_code == 401
    assert fresh_client_with(refresh=refresh).post(f"{API}/users/refresh").status_code == 401


def test_logout_all_kills_old_tokens_but_not_a_fresh_login(client, make_user):
    make_user()
    old = login(client).json()
    time.sleep(1.1)
    c = fresh_client_with(access=old["access_token"], refresh=old["refresh_token"])
    assert c.post(f"{API}/users/logout-all").status_code == 200
    assert fresh_client_with(access=old["access_token"]).get(f"{API}/users/me").status_code == 401
    assert fresh_client_with(refresh=old["refresh_token"]).post(f"{API}/users/refresh").status_code == 401
    # login immediately afterwards (possibly the same second as the marker) must work
    new = login(client).json()
    assert fresh_client_with(access=new["access_token"]).get(f"{API}/users/me").status_code == 200
    assert fresh_client_with(refresh=new["refresh_token"]).post(f"{API}/users/refresh").status_code == 200


def test_suspended_user_cannot_refresh(client, make_user):
    from app.core.database import db_manager
    import asyncio
    make_user()
    body = login(client).json()
    asyncio.run(db_manager.get_collection("users").update_one({"email": "user@example.com"}, {"$set": {"status": "suspended"}}))
    assert fresh_client_with(refresh=body["refresh_token"]).post(f"{API}/users/refresh").status_code == 401


def test_cross_origin_write_is_blocked_but_allowed_origin_and_no_origin_pass(client):
    blocked = client.post(f"{API}/users/logout", headers={"Origin": "https://evil.example"})
    assert blocked.status_code == 403
    allowed = client.post(f"{API}/users/logout", headers={"Origin": "https://houzdey.com"})
    assert allowed.status_code != 403  # reaches auth (401), not blocked by the origin check
    assert client.post(f"{API}/users/logout").status_code != 403


def test_plain_admin_cannot_escalate_but_super_admin_can(client, make_user):
    victim = make_user("victim@example.com")
    make_user("admin@example.com", role="admin")
    make_user("super@example.com", role="super_admin")
    admin = fresh_client_with(access=login(client, "admin@example.com").json()["access_token"])
    assert admin.put(f"{API}/admin/users/{victim}", json={"role": "super_admin"}).status_code == 403
    assert admin.put(f"{API}/admin/users/{victim}", json={"role": "not_a_role"}).status_code == 422
    sup = fresh_client_with(access=login(client, "super@example.com").json()["access_token"])
    assert sup.put(f"{API}/admin/users/{victim}", json={"role": "admin"}).status_code == 200


def test_mp3_frame_headers_are_recognised():
    from app.services.upload import _sniff_content_type
    for head in (b"ID3\x03", b"\xff\xfb\x90", b"\xff\xfa\x90", b"\xff\xf3\x90", b"\xff\xf2\x90"):
        assert _sniff_content_type(head) == "audio/mp3"
    assert _sniff_content_type(b"<?php echo 1;") is None


def test_regex_metacharacters_are_escaped_in_property_search():
    import asyncio
    from app.models.property import SortBy, SortOrder
    from app.repositories.property_repository import PropertyRepository

    repo = PropertyRepository()
    seen = {}

    async def fake_count(q):
        seen["q"] = q
        return 0

    async def fake_find(q, **kw):
        return []

    repo.count, repo.find = fake_count, fake_find
    asyncio.run(repo.find_with_filters(search="(a+)+$", sort_by=SortBy.CREATED_AT, sort_order=SortOrder.DESC))
    assert all(c[next(iter(c))]["$regex"] == r"\(a\+\)\+\$" for c in seen["q"]["$or"])
