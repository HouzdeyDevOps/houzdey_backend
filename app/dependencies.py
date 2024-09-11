from fastapi import Depends, HTTPException
from fastapi import Depends, HTTPException, status  # type: ignore
from app.auth_handler import decode_token, oauth2_scheme
from app.models import TokenData, PlanName
from app.crud import get_user
from app.database import property_collection, get_db_client
from motor.motor_asyncio import AsyncIOMotorCollection


# Dependency function to retrieve the current user from the provided access token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Retrieves the current user from the provided access token.
    :param token: The access token to extract the user information from.
    :return: The user data if the token is valid, an HTTPException otherwise.
    """
    # Define an HTTPException to be raised if the credentials are invalid

    # Decode the access token using the decode_token function
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token"
        )
    # Extract the user's email from the token payload
    email: str = payload.get("sub")

    # Raise an HTTPException if the email is not present in the payload
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token"
        )

    # Create a TokenData instance with the extracted email
    token_data = TokenData(email=email)

    # Retrieve the user from the database using the get_user function
    user = await get_user(email=token_data.email)

    # Raise an HTTPException if the user is not found in the database
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    # Return the user data
    return user


# user_service.py


def get_user_plan(current_user: dict = Depends(get_current_user)):
    """
    Retrieve the user's plan based on their authentication token.
    You might implement this function to fetch the user's plan from a database or cache.
    """
    # Example implementation: retrieve plan from user data
    user_plan = current_user.get("plan", PlanName.basic)
    if user_plan is None:
        raise HTTPException(status_code=404, detail="User plan not found")
    return user_plan


async def get_user_houses_count(owner_id: str) -> int:
    """
    Retrieve the count of houses posted by the user.
    You might implement this function to query your database for the count of properties owned by the user.
    """

    db = get_db_client()
    print(property_collection)

    # Assuming you have a collection for properties in your database
    property_collection = db.property_collection

    try:
        count = await property_collection.count_documents({"owner_id": owner_id})
        return count
    except Exception as e:
        print(f"An error occurred while retrieving user houses count: {e}")
        return 0  # Return a default value or handle the exception appropriately