from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File as FastAPIFile
from typing import Annotated
from helpers.import_leads_csv import humanize_results, import_leads_csv
from helpers.jwt_token import get_current_user
from models.company import Company
from models.file import File
from models.lead import Lead  
import requests

from models.user import User
from datetime import datetime
lead_router = APIRouter()

GHL_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2NhdGlvbl9pZCI6Ik82SVN0TERDTTJIcWVtNDgzN1hIIiwiY29tcGFueV9pZCI6Ik9mUDRyaUMyQ3NLVWt2bEdOYzRDIiwidmVyc2lvbiI6MSwiaWF0IjoxNjkzODUwNTk5MzUyLCJzdWIiOiJ1c2VyX2lkIn0.6Uj1OXBQZs2wVjmBktDjAtIVy-3dnRTKKjtu4La7EfU"
LOCATION_ID = "O6IStLDC2Hhqem4837XH"
BASE_URL = 'https://rest.gohighlevel.com/v1/contacts/'



@lead_router.get("/fetch-ghl-leads")
async def fetch_ghl_leads(current: Annotated[User, Depends(get_current_user)]):
    user, company = current
    headers = {
        'Authorization': f'Bearer {GHL_API_KEY}',
        'Content-Type': 'application/json'
    }

    response = requests.get(BASE_URL, headers=headers)

    if response.status_code != 200:
        print(f"Error: {response.status_code}", response.text)
        return {"error": "Failed to fetch leads"}

    data = response.json()
    leads = data.get("contacts", [])

    file_record = await File.get_or_none(company=company, type="GHL")
    if not file_record:
        file_record = await File.create(
            name="GHL Leads",
            user=user,
            company=company,
            type="GHL"
        )

    saved_count = 0
    skipped_count = 0

    for lead in leads:
        ghl_id = lead.get("id")
        phone = lead.get("phone")

        existing = await Lead.filter(
            phone =  phone
        ).first()

        if existing:
            skipped_count += 1
            continue

        name = lead.get("contactName") or f"{lead.get('firstName', '')} {lead.get('lastName', '')}".strip()
        email = lead.get("email")
        source = "GHL"
        city = lead.get("city")
        state = lead.get("state")
        country = lead.get("country")
        location_id = lead.get("locationId")
        date_added = lead.get("dateAdded")
        tags = lead.get("tags")
        other_data = lead 

        try:
            add_date = datetime.fromisoformat(date_added.replace("Z", "+00:00")) if date_added else None
        except:
            add_date = None

        await Lead.create(
            name=name,
            email=email,
            phone=phone,
            source=source,
            city=city,
            state=state,
            country=country,
            ghl_id=ghl_id,
            add_date=add_date,
            tags=tags,
            other_data=other_data,
            location_id=location_id,
            file=file_record
        )

        saved_count += 1

    return {
        "message": "Leads fetched successfully",
        "saved_count": saved_count,
        "skipped_count": skipped_count
    }

@lead_router.get("/ghl_leads")
async def get_all_leads():
    file = await File.get_or_none(type = "GHL")
    leads = await Lead.filter(file=file).order_by("-created_at").all()  
    return {
        "success": True,
        "total": len(leads),
        "data": [ 
            {
                "id": lead.id,
                "name": lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "is_called": lead.is_called,
                "source": lead.source,
                "city": lead.city,
                "state": lead.state,
                "country": lead.country,
                "ghl_id": lead.ghl_id,
                "add_date": str(lead.add_date) if lead.add_date else None,
                "tags": lead.tags,
                "location_id": lead.location_id,
                "call_count": lead.call_count,
                "last_called_at": str(lead.last_called_at) if lead.last_called_at else None,
                "created_at": str(lead.created_at),
            }
            for lead in leads
        ]
    }



@lead_router.get("/custom-leads-files")
async def list_custom_leads_files(current: Annotated[User, Depends(get_current_user)]):
    user, company = current
    files = await File.filter(company=company, type="CUSTOM").order_by("-created_at")
    return {
        "success": True,
        "total": len(files),
        "data": [
            {
                "id": f.id,
                "name": f.name,
                "type": f.type,
                "created_at": str(f.created_at),
                "updated_at": str(f.updated_at),
            }
            for f in files
        ]
    }
@lead_router.get("/leads-file")
async def list_custom_leads_files(current: Annotated[User, Depends(get_current_user)]):
    user, company = current
    files = await File.filter(company=company).order_by("-created_at")
    return {
        "success": True,
        "total": len(files),
        "data": [
            {
                "id": f.id,
                "name": f.name,
                "type": f.type,
                "created_at": str(f.created_at),
                "updated_at": str(f.updated_at),
            }
            for f in files
        ]
    }


@lead_router.get("/custom-leads/{file_id}")
async def list_custom_leads_by_file(file_id: int, current: Annotated[User, Depends(get_current_user)]):
    user, company = current
    file = await File.get_or_none(id=file_id, company=company, type="CUSTOM")
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    leads = await Lead.filter(file=file).order_by("-created_at")
    return {
        "success": True,
        "file": {
            "id": file.id,
            "name": file.name,
            "type": file.type,
            "created_at": str(file.created_at),
            "updated_at": str(file.updated_at),
        },
        "total": len(leads),
        "data": [
            {
                "id": lead.id,
                "name": lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "city": lead.city,
                "state": lead.state,
                "country": lead.country,
                "add_date": str(lead.add_date) if lead.add_date else None,
                "created_at": str(lead.created_at),
                "status": lead.is_called,
            }
            for lead in leads
        ]
    }


@lead_router.post("/custom-leads-file")
async def import_leads_file(current: Annotated[User, Depends(get_current_user)], 
                             file: UploadFile = FastAPIFile(...), name: str = Form(...)):
    try:  
        user, company  = current
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8")
        
        

        if file.filename.split(".")[-1] != "csv":
            raise HTTPException(
                status_code=400,
                detail="Unsupported Format. Only CSV files are allowed."
            )
        
     
        return await process_file_upload(content, file, name, user,company)



    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@lead_router.delete("/custom-leads-file/{id}")
async def delete_file(id: int,current: Annotated[User, Depends(get_current_user)],
):
  try:
        user, company = current
        file = await File.get_or_none(id=id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        await file.delete()
        await Lead.filter(file=file).delete()
    
        return { "success": True, "detail": "File deleted successfully." }
  except Exception as e: 
         raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )



















async def process_file_upload(content: str, file: UploadFile, name: str, user: User, company : Company):
    try:
        
        file_record = File(name=name, user=user, company=company, type = "CUSTOM")
        await file_record.save()
        results = await import_leads_csv(content, file_record)
        
        return {  
            "success": True,
            "results": results,
            "detail": humanize_results(results),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )