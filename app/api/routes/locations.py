from fastapi import APIRouter, Depends
from typing import List
from ...services.location_service import LocationService

router = APIRouter()

@router.get("/states", response_model=List[str])
async def get_states(
    location_service: LocationService = Depends(LocationService)
):
    return await location_service.get_states()

@router.get("/states/{state}/lgas", response_model=List[str])
async def get_lgas(
    state: str,
    location_service: LocationService = Depends(LocationService)
):
    return await location_service.get_lgas(state)

@router.get("/states/{state}/lgas/{lga}/wards", response_model=List[str])
async def get_wards(
    state: str,
    lga: str,
    location_service: LocationService = Depends(LocationService)
):
    return await location_service.get_wards(state, lga)