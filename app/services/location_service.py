from typing import List
from fastapi import HTTPException
from ..core.database import db_manager

class LocationService:
    def __init__(self):
        self.states_collection = db_manager.get_collection("states")

    async def get_states(self) -> List[str]:
        try:
            cursor = self.states_collection.find({}, {"_id": 0, "name": 1})
            states = await cursor.to_list(length=None)
            return [state["name"] for state in states]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_lgas(self, state: str) -> List[str]:
        try:
            state_doc = await self.states_collection.find_one(
                {"name": state.lower()},
                {"_id": 0, "lgas": 1}
            )
            if not state_doc:
                return []
            return [lga["name"] for lga in state_doc.get("lgas", [])]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_wards(self, state: str, lga: str) -> List[str]:
        try:
            state_doc = await self.states_collection.find_one(
                {"name": state.lower(), "lgas.name": lga.lower()},
                {"_id": 0, "lgas.$": 1}
            )
            if not state_doc or not state_doc.get("lgas"):
                return []
            return state_doc["lgas"][0].get("wards", [])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) 