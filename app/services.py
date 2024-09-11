from bson import ObjectId, objectid
from fastapi import HTTPException, status
from app.database import property_collection
from schemas.serializeObjects import serializeDict, serializeList


_notFoundMessage = "Could not find property with the given Id."


async def getAllProperties() -> list:
    return serializeList(property_collection.find())


# async def getById(id):
#     return serializeDict(property_collection.find_one({"_id": ObjectId(id)}))

async def getById(id):
    result = await property_collection.find_one({"_id": ObjectId(id)})
    if result:
        return await serializeDict(result)
    else:
        return None


async def resultVerification(id: objectid) -> dict:
    result = await getById(id)
    await riseHttpExceptionIfNotFound(result, message=_notFoundMessage)
    return result


async def riseHttpExceptionIfNotFound(result, message: str):
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=message)


async def savePicture(id, imageUrl: str) -> bool:
    await property_collection.find_one_and_update({"_id": ObjectId(id)}, {
        "$set": {"imageUrl": imageUrl}})
    return True


def getResponse(done: bool, errorMessage: str):
    if not done:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=errorMessage)
    return None
