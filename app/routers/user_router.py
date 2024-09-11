from typing import Any, Annotated, Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from app.settings import settings
from app.models import User
from fastapi.responses import JSONResponse
from app.crud import (
    add_to_wishlist,
    get_all_users,
    get_user,
    get_user_by_id,
    register_user,
    remove_from_wishlist,
)
from passlib.context import CryptContext  # type: ignore
from app.dependencies import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from app.database import get_db_client, user_collection
from bson import ObjectId


from app.utils import (
    create_token,
    verify_token,
    generate_verification_email,
    send_email,
)
from fastapi import File, UploadFile
import boto3  # type: ignore
from botocore.client import Config
from fastapi import Response
from botocore.exceptions import NoCredentialsError


router = APIRouter(prefix="/api", tags=["users"])

# Initialize Passlib's CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


s3 = boto3.client(
    "s3",
    region_name="eu-north-1",
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    config=Config(signature_version="s3v4"),
)


# POST /signup endpoint to create a new user
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_user(user: User):
    """Create a new user."""
    try:
        # Check if email already exists
        existing_user = await get_user(
            user.email
        )  # If this doesn't throw an error then the email is already registered
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")

        # Hash the user's password using bcrypt
        hashed_password = pwd_context.hash(user.password)

        # generate token
        email_verification_token = create_token(
            subject=user.email, type_ops="verify"
        )  # noqa

        # Prepare user data for registration
        user_data = user.model_dump()
        user_data["password"] = hashed_password
        user_data["phone_number"] = user_data["phone_number"].split(":")[1]
        user_data["wishlist"] = []
        user_data["is_active"] = False
        user_data["plan"] = "Basic"
        user_data["profile_picture"] = ""

        await register_user(user_data)

        # send email verification to user
        email_data = generate_verification_email(
            email_to=user.email, email=user.email, token=email_verification_token
        )

        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )

        # return new_user
        # Return a success message
        return {"message": "User registered successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-email/{token}")
async def verify_email(
    token: str, db: Annotated[OAuth2PasswordRequestForm, Depends(get_db_client)]
):
    # verify token
    email = verify_token(token=token)

    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await get_user(email=email)

    if not user:
        raise HTTPException(status_code=500, detail="The user with this email does not exist in the system.")

    # Access the ObjectId value properly
    user_id = ObjectId(user["id"])
    await user_collection.update_one({"_id": user_id}, {"$set": {"is_active": True}})

    return JSONResponse(status_code=201, content={"message": "Email verified"})


# GET / endpoint to retrieve all users
@router.get("/")
async def get_all_users_route():
    """Get all users."""
    return await get_all_users()


# GET /me endpoint to retrieve the current user response_model=UserResponse
@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get the current user."""
    return current_user


# GET /{user_id} endpoint to retrieve a user by ID
@router.get("/{user_id}", response_model=User)
async def get_user_by_id_route(user_id: Any):
    """Get user by ID."""
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/user/wishlist/", status_code=status.HTTP_201_CREATED)
async def add_listing_to_wishlist(
    property_id: str, current_user=Depends(get_current_user)
):
    await add_to_wishlist(str(current_user["id"]), property_id)

    return {"message": "Property added to wishlist"}


@router.delete("/user/wishlist/", status_code=status.HTTP_200_OK)
async def remove_listing_from_wishlist(
    property_id: str, current_user=Depends(get_current_user)
):
    await remove_from_wishlist(str(current_user["id"]), property_id)

    return {"message": "Property removed from wishlist"}


@router.post("/user/profile-picture")
async def upload_profile_picture(
    profile_picture: UploadFile = File(...), current_user=Depends(get_current_user)
):
    # Save the profile picture to S3 and get its key
    image_key = f"profile images/{str(current_user['id'])}/{profile_picture.filename}"
    s3.upload_fileobj(profile_picture.file, settings.BUCKET_NAME, image_key)

    # Update the user document in MongoDB with the image key
    await user_collection.update_one(
        {"_id": ObjectId(current_user["id"])}, {"$set": {"profile_picture": image_key}}
    )
    return {"message": "Profile picture uploaded"}


@router.get("/user/profile-picture")
async def get_profile_picture(current_user=Depends(get_current_user)):
    # Get the user document from MongoDB
    user = await user_collection.find_one({"_id": ObjectId(current_user["id"])})

    # Check if the user has a profile picture
    if "profile_picture" not in user or not user["profile_picture"]:
        return {"message": "No profile picture found"}

    # Get the image key
    image_key = user["profile_picture"]

    # Get the image from S3
    try:
        file_obj = s3.get_object(Bucket=settings.BUCKET_NAME, Key=image_key)
    except NoCredentialsError:
        return {"message": "Missing S3 credentials"}

    # Return the image as a response
    return Response(file_obj["Body"].read(), media_type="image/jpeg")


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None


@router.put("/user")
async def update_account(
    user_update: UserUpdate, current_user=Depends(get_current_user)
):
    # Create the update document
    update_doc = user_update.dict(exclude_unset=True)

    # Update the user document in MongoDB
    result = await user_collection.update_one(
        {"_id": ObjectId(current_user["id"])}, {"$set": update_doc}
    )

    # Check if a document was updated
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return {"message": "Account updated"}


@router.delete("/user")
async def delete_account(current_user=Depends(get_current_user)):
    # Get the user document from MongoDB
    user = await user_collection.find_one({"_id": ObjectId(current_user["id"])})

    # Check if the user has a profile picture
    if "profile_picture" in user:
        # Get the image key
        image_key = user["profile_picture"]

        # Delete the image from S3
        try:
            s3.delete_object(Bucket=settings.BUCKET_NAME, Key=image_key)
        except NoCredentialsError:
            return {"message": "Missing S3 credentials"}

    # Delete the user document from MongoDB
    result = await user_collection.delete_one({"_id": ObjectId(current_user["id"])})

    # Check if a document was deleted
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return {"message": "Account and profile picture deleted"}
