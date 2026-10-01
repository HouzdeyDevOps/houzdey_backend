import asyncio
import os

import pytest

os.environ.update({
    "SECRET_KEY": "test-secret-key-test-secret-key-1234",
    "MONGO_URL": "mongodb://localhost:27017/test",
    "CLOUDINARY_CLOUD_NAME": "x", "CLOUDINARY_API_KEY": "x", "CLOUDINARY_API_SECRET": "x",
    "CLOUDINARY_URL": "cloudinary://x:x@x",
    "GOOGLE_CLIENT_ID": "x", "GOOGLE_CLIENT_SECRET": "x", "GOOGLE_REDIRECT_URI": "http://localhost/cb",
    "BREVO_SMTP_USERNAME": "x", "BREVO_SMTP_PASSWORD": "x", "EMAIL_FROM": "test@example.com",
    "TERMII_API_KEY": "x", "ENVIRONMENT": "local",
})

# Swap Motor for an in-memory Mongo BEFORE the app (and its module-level collections) is imported.
import motor.motor_asyncio as motor_module  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

motor_module.AsyncIOMotorClient = AsyncMongoMockClient

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import db_manager  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from main import app  # noqa: E402
import app.api.routes.users as users_routes  # noqa: E402

PASSWORD = "Passw0rd!Passw0rd"


@pytest.fixture(autouse=True)
def clean_db():
    users_routes.limiter.enabled = False
    db = db_manager.database

    async def wipe():
        for name in await db.list_collection_names():
            await db.drop_collection(name)

    asyncio.run(wipe())
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def make_user():
    def _make(email="user@example.com", role="user", status="verified"):
        doc = {
            "email": email, "password": get_password_hash(PASSWORD), "first_name": "T", "last_name": "U",
            "status": status, "role": role, "is_active": True, "email_verified": True,
            "phone_verified": False, "wishlist": [], "plan": "Basic", "profile_picture": "",
        }
        result = asyncio.run(db_manager.get_collection("users").insert_one(doc))
        return str(result.inserted_id)
    return _make
