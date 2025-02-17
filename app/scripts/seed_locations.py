import json
import asyncio
from ..core.database import houzdey_database

async def seed_locations():
    collection = houzdey_database.states

    # First, clear existing data
    await collection.delete_many({})

    # Read the JSON file
    with open("app/data/states-and-lgas-and-wards.json", "r") as f:
        location_data = json.load(f)

    # Transform and insert data
    states_to_insert = []
    for state in location_data:
        state_doc = {
            "name": state["state"].lower(),
            "lgas": [
                {
                    "name": lga["lga"].lower(),
                    "wards": [ward.lower() for ward in lga["wards"]]
                }
                for lga in state["lgas"]
            ]
        }
        states_to_insert.append(state_doc)

    # Insert all states
    await collection.insert_many(states_to_insert)
    print("Location data seeded successfully")

if __name__ == "__main__":
    asyncio.run(seed_locations()) 