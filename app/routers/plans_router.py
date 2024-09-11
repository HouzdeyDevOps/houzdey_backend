from fastapi import Query
from fastapi import APIRouter, Depends, HTTPException, Path
from app.models import pricing_plans_db, PlanBase, User, UserRegister
from typing import Dict, Optional, Annotated
from app.dependencies import get_current_user, get_user_plan
from app.database import user_collection, property_collection
from bson import ObjectId


router = APIRouter(prefix="/api/v1/plans", tags=["pricing-plans"])


# Endpoint to get pricing plans
@router.get("/", response_model=Dict[str, PlanBase])
async def get_pricing_plans():
    plans_dict = {plan['name']: PlanBase(**plan) for plan in pricing_plans_db}
    return plans_dict


@router.post("/upgrade_plan")
async def upgrade_plan(
    current_user=Depends(get_current_user)

):
    all_properties_cursor = property_collection.find()
    all_properties = await all_properties_cursor.to_list(length=None)

    user_properties = [
        x for x in all_properties if x['owner_id'] == str(current_user["id"])]

    # Define plan limits
    plan_limits = {
        'Basic': 2,
        'Standard': 7,
        'Premium': 12
    }

    # Check if user has reached the limit for their plan
    for plan, limit in plan_limits.items():
        if len(user_properties) >= limit and ('plan' not in current_user or current_user['plan'] == plan):
            # Upgrade plan to the next higher plan
            if plan == 'Basic':
                current_user['plan'] = 'Standard'
                user_id = ObjectId(current_user["id"])
                await user_collection.update_one({"_id": user_id}, {"$set": {"plan": "Standard"}})
            elif plan == 'Standard':
                current_user['plan'] = 'Premium'
                user_id = ObjectId(current_user["id"])
                await user_collection.update_one({"_id": user_id}, {"$set": {"plan": "Premium"}})
            else:
                raise HTTPException(
                    status_code=400,
                    detail="You have reached the maximum plan limit."
                )
            return {"message": f"Plan upgraded to {current_user['plan']}"}

    return {"message": "No upgrade needed."}
