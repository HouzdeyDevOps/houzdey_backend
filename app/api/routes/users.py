from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from app.models.user import User, UserCreate, UserVerify, UserLogin, UserStatus
from fastapi.responses import JSONResponse
from app.crud import get_user, create_user, update_user
from passlib.context import CryptContext  # type: ignore
from app.api.deps import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from app.core.database import get_db_client, user_collection
from bson import ObjectId
from app.core.security import create_verification_code, verify_password, create_token, get_password_hash
from pydantic import ValidationError
from app.core.security import verify_token, verify_code
from app.utils.email import send_verification_code
from fastapi import File, UploadFile
from app.utils.cloudinary_config import upload_image_to_cloudinary
from datetime import datetime, timedelta
import random
import string
from app.core.config import settings

router = APIRouter()

# Initialize Passlib's CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# POST /signup endpoint to create a new user
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_new_user(user: UserCreate):
    """Create a new user."""
    try:
        # Check if email already exists
        existing_user = await get_user(
            user.email
        )  # If this doesn't throw an error then the email is already registered
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")

        # Generate verification code
        verification_code = create_verification_code()
        code_expiry = datetime.utcnow() + timedelta(minutes=10)

        # Create user with verification code
        user_data = user.model_dump()
        user_data.update(
            {
                "verification_code": verification_code,
                "code_expiry": code_expiry,
                "email_verified": False,
            }
        )

        # Create user in database
        new_user = await create_user(user_data)

        # Send verification code
        await send_verification_code(user.email, verification_code)

        return {
            "message": "Registration successful. Please check your email to verify your account.",
            "user_id": str(new_user.id),
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# login route
@router.post("/signin", response_model=dict)
async def login_user(user_credentials: UserLogin):
    """Authenticate a user and return a token."""
    try:
        # Get user from database
        user = await get_user(user_credentials.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        # Verify password
        if not verify_password(user_credentials.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Check if user is verified
        if user.status == UserStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Please verify your email before signing in",
                    "email": user.email,
                    "status": "unverified"
                }
            )

        # Create access token
        access_token = create_token(subject=user.email, type_ops="access")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "status": user.status,
                "role": user.role,  # Add role to login response
                "profile_picture": user.profile_picture,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/verify-code")
async def verify_user_code(verification: UserVerify):
    """Verify user's email with code"""
    try:
        user = await get_user(verification.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_code(user, verification.code):
            raise HTTPException(status_code=400, detail="Invalid or expired code")

        # Update user verification status
        success = await update_user(
            user.id,
            {
                "email_verified": True,
                "verification_code": None,
                "code_expiry": None,
                "status": "verified",
            },
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to update user verification status"
            )

        return {"message": "Email verified successfully"}
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# /users/resend-code
@router.post("/resend-code")
async def resend_code(email: str):
    """Resend verification code"""
    try:
        verification_code = create_verification_code()
        code_expiry = datetime.utcnow() + timedelta(minutes=10)

        user = await get_user(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await update_user(
            user.id,
            {
                "verification_code": verification_code,
                "code_expiry": code_expiry,
            },
        )
        await send_verification_code(email, verification_code)
        return {"message": "Verification code resent successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/resend-verification")
async def resend_verification(email: str = Query(..., description="Email to resend verification to")):
    """Resend verification email"""
    try:
        user = await get_user(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if user.status == UserStatus.VERIFIED:
            raise HTTPException(status_code=400, detail="Email is already verified")

        verification_code = create_verification_code()
        code_expiry = datetime.utcnow() + timedelta(minutes=10)

        await update_user(
            user.id,
            {
                "verification_code": verification_code,
                "code_expiry": code_expiry,
            },
        )
        
        await send_verification_code(email, verification_code)
        return {"message": "Verification code resent successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )


@router.post("/verify-email/{token}")
async def verify_email(
    token: str, db: Annotated[OAuth2PasswordRequestForm, Depends(get_db_client)]
):
    # verify token
    email = verify_token(token, expected_type="verify")

    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await get_user(email=email)

    if not user:
        raise HTTPException(
            status_code=500,
            detail="The user with this email does not exist in the system.",
        )

    # Access the ObjectId value properly
    user_id = ObjectId(user["id"])
    await user_collection.update_one({"_id": user_id}, {"$set": {"is_active": True}})

    return JSONResponse(status_code=201, content={"message": "Email verified"})


# GET /me endpoint to retrieve the current user response_model=UserResponse
@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get the current user."""
    return current_user


@router.post("/upload-profile-picture")
async def upload_profile_picture(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
):
    try:
        # Upload to Cloudinary
        image_url = await upload_image_to_cloudinary(
            await file.read(), folder=f"profile_pictures/{current_user['id']}"
        )

        # Update user's profile picture URL in database
        await user_collection.update_one(
            {"_id": ObjectId(current_user["id"])},
            {"$set": {"profile_picture": image_url}},
        )

        return {"profile_picture_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/personal-info")
async def update_personal_info(
    email: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_number: str = Form(...),
    date_of_birth: str = Form(...),
    profile_picture: UploadFile = File(None),
):
    """Update user's personal information"""
    try:
        user = await get_user(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.status != UserStatus.VERIFIED:
            raise HTTPException(status_code=400, detail="Email not verified")

        # Upload profile picture to Cloudinary if provided
        profile_picture_url = None
        if profile_picture:
            try:
                contents = await profile_picture.read()
                profile_picture_url = await upload_image_to_cloudinary(
                    contents, folder=f"profile_pictures/{user.id}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload profile picture: {str(e)}",
                )

        # Update user with personal info
        update_data = {
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "date_of_birth": datetime.strptime(date_of_birth, "%Y-%m-%d"),
            # "status": "complete",
            "is_active": True,
            "profile_picture": profile_picture_url,
        }

        # Only add profile picture URL if an image was uploaded
        if profile_picture_url:
            update_data["profile_picture"] = profile_picture_url

        await update_user(user.id, update_data)

        return {
            "message": "Personal information updated successfully",
            "profile_picture_url": profile_picture_url if profile_picture_url else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/forgot-password")
async def forgot_password(email: str = Form(...)):
    """
    Send a password reset OTP code to the user's email
    """
    try:
        # Check if user exists
        user = await get_user(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email does not exist"
            )

        # Generate verification code
        reset_code = create_verification_code()
        code_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        # Update user with reset code
        await user_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "verification_code": reset_code,
                    "code_expiry": code_expiry
                }
            }
        )
        
        # Generate and send reset password email with OTP
        try:
            await send_verification_code(email, reset_code, purpose="reset")
            return {"message": "Password reset code sent successfully"}
        except Exception as e:
            # Log the error but don't expose internal error details
            print(f"Failed to send reset password code: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send reset password code. Please try again later."
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Unexpected error in forgot_password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )

@router.post("/reset-password")
async def reset_password(
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...)
):
    """
    Reset user's password using the OTP code
    """
    try:
        # Get user and verify code
        user = await get_user(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        # Convert user to dict
        user.model_dump()


        # Verify the reset code
        if not verify_code(user, code, code_type="reset"):
            print("Code verification failed")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code"
            )


        # Hash new password
        hashed_password = get_password_hash(new_password)
        
        # Update user's password and clear reset code
        update_result = await user_collection.update_one(
            {"email": email},
            {
                "$set": {"password": hashed_password},
                "$unset": {"reset_code": "", "reset_code_expiry": ""}
            }
        )

        if update_result.modified_count == 0:
            print("Failed to update password in database")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )

        print("Password updated successfully")
        return {"message": "Password reset successful"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in reset_password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )

# OAuth2 token endpoint for Swagger UI
@router.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token login, get an access token for future requests."""
    try:
        # Get user from database
        user = await get_user(form_data.username)  # username field contains email
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Verify password
        if not verify_password(form_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Check if user is verified
        if user.status == UserStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified"
            )

        # Create access token
        access_token = create_token(subject=user.email, type_ops="access")

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Phone verification endpoints
@router.post("/phone/send-otp")
async def send_phone_otp(phone_number: str = Form(...), current_user: User = Depends(get_current_user)):
    """Send OTP to user's phone number"""
    try:
        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        expiry = datetime.utcnow() + timedelta(minutes=10)


        # Update user with OTP
        success = await update_user(
            current_user.id,
            {
                "phone_number": phone_number,
                "verification_code": otp,
                "code_expiry": expiry,
            },
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to update user phone verification data"
            )

        # TODO: Integrate with SMS service to send OTP
        # For now, just return the OTP in local (development)
        if settings.ENVIRONMENT == "local":
            return {"message": "OTP sent successfully", "otp": otp}
        
        return {"message": "OTP sent successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

@router.post("/phone/verify")
async def verify_phone_otp(
    phone_number: str = Form(...),
    otp: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """Verify phone number with OTP"""
    try:
        # Verify OTP
        if (
            not current_user.verification_code
            or not current_user.code_expiry
            or current_user.verification_code != otp
            or datetime.utcnow() > current_user.code_expiry
            or current_user.phone_number != phone_number
        ):
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")

        # Update user verification status
        success = await update_user(
            current_user.id,
            {
                "phone_verified": True,
                "verification_code": None,
                "code_expiry": None,
            },
        )

        print(success)

        # if not success:
        #     raise HTTPException(
        #         status_code=500, detail="Failed to update phone verification status"
        #     )

        return {"message": "Phone number verified successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
