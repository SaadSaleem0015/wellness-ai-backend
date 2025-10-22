from fastapi import APIRouter, HTTPException
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from models.lead import Lead  # your Lead model, with async DB methods etc
import requests
lead_router = APIRouter()

# === CONFIG ===
GHL_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2NhdGlvbl9pZCI6Ik82SVN0TERDTTJIcWVtNDgzN1hIIiwiY29tcGFueV9pZCI6Ik9mUDRyaUMyQ3NLVWt2bEdOYzRDIiwidmVyc2lvbiI6MSwiaWF0IjoxNjkzODUwNTk5MzUyLCJzdWIiOiJ1c2VyX2lkIn0.6Uj1OXBQZs2wVjmBktDjAtIVy-3dnRTKKjtu4La7EfU"
GHL_BASE_URL = "https://services.leadconnectorhq.com"
LOCATION_ID = "O6IStLDC2Hhqem4837XH"


@lead_router.get("/leads")
async def fetch_ghl_leads(
    after: Optional[str] = None, 
    limit: int = 100
):
    """
    Fetch leads (contacts) from GoHighLevel using API key, and upsert into your DB.
    `after` is an ISO datetime string for filtering leads updated/created after that point.
    """
    headers = {
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        # It might be required to include a Version header — many users report that “version header not found” errors occur. :contentReference[oaicite:0]{index=0}
        "Version": "2021-07-28"
    }

    params: Dict[str, Any] = {
        "locationId": LOCATION_ID,
        "limit": limit
    }

    # If no "after" provided, default to 7 days ago
    if not after:
        after_dt = datetime.utcnow() - timedelta(days=7)
        # Format to ISO + “Z” for UTC
        after = after_dt.isoformat() + "Z"
    params["after"] = after

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{GHL_BASE_URL}/contacts/search", headers=headers, params=params)

        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid or expired API key / unauthorized.")
        if resp.status_code != 200:
            # show the whole body for debugging
            raise HTTPException(status_code=resp.status_code, detail=f"GHL error: {resp.text}")

        data = resp.json()
        contacts = data.get("contacts", [])

        processed = []
        # process + save in DB
        for c in contacts:
            # Build your lead data mapping — modify fields as your model expects
            lead_data = {
                "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
                "email": c.get("email"),
                "phone": c.get("phone"),
                "other_data": c,  # you can save full JSON if you want
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                # you could also include a field like “ghl_id” if your Lead model has it
                "ghl_id": c.get("id")
            }

            # You need to adapt this to your Lead model / ORM (async or sync)
            # Example with “get_or_create” pattern:
            lead, created = await Lead.get_or_create(
                ghl_id=lead_data["ghl_id"],
                defaults=lead_data
            )
            if not created:
                # update existing
                await lead.update_from_dict(lead_data)
                await lead.save()

            processed.append({
                "ghl_id": lead_data["ghl_id"],
                "created": created
            })

        return {
            "total_fetched": len(contacts),
            "processed": processed,
            "raw": contacts
        }

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")




@lead_router.get("/fetch-leads")
async def fetch_ghl_leads(
):
    BASE_URL = 'https://rest.gohighlevel.com/v1/contacts/'
    headers = {
        'Authorization': f'Bearer {GHL_API_KEY}',
        'Content-Type': 'application/json'
    }

    response = requests.get(BASE_URL, headers=headers)
    if response.status_code == 200:
        leads = response.json()['contacts']
        return leads
    else:
        print(f"Error: {response.status_code}", response.text)