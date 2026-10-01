import asyncio
import time

from app.core.database import db_manager
from tests.conftest import PASSWORD
from tests.test_auth import API, fresh_client_with, login

SECRETS = ("password", "reset_code", "reset_code_expiry", "verification_code", "code_expiry",
           "phone_otp", "phone_otp_expiry", "phone_otp_number", "code_attempts")


def users():
    return db_manager.get_collection("users")


def set_fields(email, fields):
    asyncio.run(users().update_one({"email": email}, {"$set": fields}))


def get_user(email):
    return asyncio.run(users().find_one({"email": email}))


def auth_as(client, email):
    return fresh_client_with(access=login(client, email).json()["access_token"])


def test_admin_user_endpoints_never_return_secret_fields(client, make_user):
    victim = make_user("victim@example.com")
    make_user("admin@example.com", role="admin")
    set_fields("victim@example.com", {
        "reset_code": "123456", "reset_code_expiry": 1, "verification_code": "654321",
        "code_expiry": 1, "phone_otp": "111111", "phone_otp_expiry": 1, "code_attempts": 2,
    })
    admin = auth_as(client, "admin@example.com")
    listing = admin.get(f"{API}/admin/users").json()
    detail = admin.get(f"{API}/admin/users/{victim}").json()
    rows = listing if isinstance(listing, list) else listing.get("users", [])
    for doc in rows + [detail]:
        assert not [f for f in SECRETS if f in doc], f"secret fields leaked: {doc.keys()}"


def test_suspending_a_user_ends_their_sessions_and_blocks_login(client, make_user):
    victim = make_user("victim@example.com")
    make_user("admin@example.com", role="admin")
    tokens = login(client, "victim@example.com").json()
    time.sleep(1.1)  # the logout marker is whole-second precision
    admin = auth_as(client, "admin@example.com")
    assert admin.post(f"{API}/admin/users/{victim}/suspend", json={"reason": "abuse"}).status_code == 200
    assert fresh_client_with(access=tokens["access_token"]).get(f"{API}/users/me").status_code == 401
    assert fresh_client_with(refresh=tokens["refresh_token"]).post(f"{API}/users/refresh").status_code == 401
    r = client.post(f"{API}/users/login", json={"email": "victim@example.com", "password": PASSWORD})
    assert r.status_code != 200


def test_suspended_status_alone_blocks_an_unexpired_token(client, make_user):
    make_user("victim@example.com")
    tokens = login(client, "victim@example.com").json()
    set_fields("victim@example.com", {"status": "suspended"})
    assert fresh_client_with(access=tokens["access_token"]).get(f"{API}/users/me").status_code == 401


def test_plain_admin_cannot_suspend_an_admin_or_super_admin(client, make_user):
    sup = make_user("super@example.com", role="super_admin")
    make_user("admin@example.com", role="admin")
    admin = auth_as(client, "admin@example.com")
    assert admin.post(f"{API}/admin/users/{sup}/suspend", json={"reason": "x"}).status_code == 403
    assert get_user("super@example.com")["status"] == "verified"


def test_verify_email_code_is_invalidated_after_five_wrong_attempts(client, make_user):
    make_user("new@example.com", status="pending")
    set_fields("new@example.com", {"is_active": False, "email_verified": False, "verification_code": "123456",
                                   "code_expiry": None})
    for _ in range(4):
        assert client.post(f"{API}/users/verify", json={"email": "new@example.com", "code": "000000"}).status_code == 400
    last = client.post(f"{API}/users/verify", json={"email": "new@example.com", "code": "000000"})
    assert last.status_code == 400
    # the right code no longer works: it was invalidated, and the attempt counter reset
    ok = client.post(f"{API}/users/verify", json={"email": "new@example.com", "code": "123456"})
    assert ok.status_code == 400
    assert get_user("new@example.com").get("verification_code") is None


def test_reset_code_is_invalidated_after_five_wrong_attempts(client, make_user):
    make_user("a@example.com")
    set_fields("a@example.com", {"reset_code": "123456", "reset_code_expiry": None})
    form = {"email": "a@example.com", "new_password": "NewPassw0rd!NewPassw0rd"}
    for _ in range(5):
        assert client.post(f"{API}/users/reset-password", data={**form, "reset_code": "000000"}).status_code == 400
    assert client.post(f"{API}/users/reset-password", data={**form, "reset_code": "123456"}).status_code == 400


def test_successful_reset_ends_existing_sessions(client, make_user):
    make_user("a@example.com")
    old = login(client, "a@example.com").json()
    time.sleep(1.1)
    set_fields("a@example.com", {"reset_code": "123456", "reset_code_expiry": None})
    r = client.post(f"{API}/users/reset-password",
                    data={"email": "a@example.com", "reset_code": "123456", "new_password": "NewPassw0rd!NewPassw0rd"})
    assert r.status_code == 200, r.text
    assert fresh_client_with(access=old["access_token"]).get(f"{API}/users/me").status_code == 401
    assert fresh_client_with(refresh=old["refresh_token"]).post(f"{API}/users/refresh").status_code == 401


def test_phone_otp_only_verifies_the_number_it_was_sent_to(client, make_user):
    make_user("a@example.com")
    c = auth_as(client, "a@example.com")
    set_fields("a@example.com", {"phone_otp": "111111", "phone_otp_number": "+2348000000001",
                                 "phone_otp_expiry": None})
    # wrong number with the right OTP: rejected
    other = c.post(f"{API}/users/phone/verify", data={"phone_number": "+2348000000002", "otp": "111111"})
    assert other.status_code == 400
    assert get_user("a@example.com").get("phone_verified") in (False, None)


def test_phone_otp_attempts_are_capped(client, make_user):
    make_user("a@example.com")
    c = auth_as(client, "a@example.com")
    future = __import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(minutes=10)
    set_fields("a@example.com", {"phone_otp": "111111", "phone_otp_number": "+2348000000001",
                                 "phone_otp_expiry": future})
    for _ in range(5):
        assert c.post(f"{API}/users/phone/verify",
                      data={"phone_number": "+2348000000001", "otp": "000000"}).status_code == 400
    # OTP wiped after too many tries: the correct code is now useless
    assert c.post(f"{API}/users/phone/verify",
                  data={"phone_number": "+2348000000001", "otp": "111111"}).status_code == 400


def test_phone_otp_for_the_right_number_verifies(client, make_user):
    make_user("a@example.com")
    c = auth_as(client, "a@example.com")
    future = __import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(minutes=10)
    set_fields("a@example.com", {"phone_otp": "111111", "phone_otp_number": "+2348000000001",
                                 "phone_otp_expiry": future})
    ok = c.post(f"{API}/users/phone/verify", data={"phone_number": "+2348000000001", "otp": "111111"})
    assert ok.status_code == 200, ok.text
    assert get_user("a@example.com")["phone_verified"] is True
