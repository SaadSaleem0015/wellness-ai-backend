import datetime
from typing import List,Annotated
from fastapi import Depends, HTTPException,APIRouter
import httpx
from pydantic import BaseModel
from helpers.jwt_token import get_current_user
from twilio.rest import Client
from tortoise.transactions import in_transaction
import os 
import dotenv
from helpers.vapi_helper import get_headers
import requests
from helpers.jwt_token import get_current_user
from models.user import User
from models.assistant import Assistant
from models.purchased_number import PurchasedNumber
from models.user import User


dotenv.load_dotenv()
twilio_router = APIRouter()

class AvailablePhoneNumberRequest(BaseModel):
    area_code: str
    country :str

class PurchaseNumberRequest(BaseModel):
    phone_number: List[str]
class RemoveNumberRequest(BaseModel):
    phone_number: str
class PhoneNumberRequest(BaseModel):
    country:str
    area_codes: List[str]  
class PurchaseNumberRequest(BaseModel):
    phone_number: List[str]  
    
    

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']

client = Client(account_sid, auth_token)


@twilio_router.get("/vapi-phone-numbers")
async def get_vapi_phone_numbers(current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company = current
        url = "https://api.vapi.ai/phone-number"
        response = requests.get(url, headers=get_headers())

        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch phone numbers from Vapi API: {response.text}"
            )

        data = response.json()
        purchased_numbers = []

        for num in data:
            vapi_phone_uuid = num.get("id")
            phone_number = num.get("number")
            friendly_name = num.get("name")

            existing = await PurchasedNumber.get_or_none(
                phone_number=phone_number, company=company
            )
            if existing:
                continue

            # Save to DB
            purchased_entry = await PurchasedNumber.create(
                user=user,
                company=company,
                phone_number=phone_number,
                vapi_phone_uuid=vapi_phone_uuid,
                friendly_name=friendly_name,
                region=None,
                postal_code=None,
                iso_country=None,
            )

            purchased_numbers.append(purchased_entry.phone_number)

        return {
            "success": True,
            "total_saved": len(purchased_numbers),
            "saved_numbers": purchased_numbers
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching or saving phone numbers: {str(e)}"
        )


@twilio_router.post("/number_info")
def check_sms_capability(phone_number_sid: str):
    try:
        phone_number = client.incoming_phone_numbers(phone_number_sid).fetch()
        if phone_number.sms_enabled:
            return {"sms_capable": True, "phone_number": phone_number.phone_number}
        else:
            return {"sms_capable": False, "phone_number": phone_number.phone_number}
    
    except Exception as e:
        return {"error": str(e)}

@twilio_router.post("/available_phone_numbers")
async def buy_phone_number(request : AvailablePhoneNumberRequest, user: Annotated[User, Depends(get_current_user)]):
    available_numbers = []
    
       
    numbers_for_area_code = client.available_phone_numbers(request.country).local.list(area_code = request.area_code)

    if numbers_for_area_code:
            for number in numbers_for_area_code:
                available_numbers.append({
                    "friendly_name": number.friendly_name,
                    "phone_number": number.phone_number,
                    "region": number.region,
                    "postal_code": number.postal_code,
                    "iso_country": number.iso_country,
                    "capabilities": number.capabilities
                })

    return available_numbers


   
@twilio_router.post("/purchase_phone_number")
async def purchase_phone_number(request: PurchaseNumberRequest, current: Annotated[User, Depends(get_current_user)]):
    try:
        SMS_URL = os.getenv("SMS_URL")
        async with in_transaction():
            user,company = current

            purchased_numbers = []
            for phone_number in request.phone_number:
                purchased_number = client.incoming_phone_numbers.create(
                    phone_number=phone_number
                )
                client.incoming_phone_numbers(purchased_number.sid).update(
                    sms_url=SMS_URL
                )
                attach_payload = {
                    "provider": "twilio",
                    "number": purchased_number.phone_number,
                    "twilioAccountSid": os.environ.get('TWILIO_ACCOUNT_SID'),
                    "twilioAuthToken": os.environ.get('TWILIO_AUTH_TOKEN'),
                    "name": "Twilio Number",
                }
              
                attach_url = os.environ.get('VAPI_ATTACH_PHONE_URL')
                if not attach_url:
                    raise HTTPException(status_code=500, detail="Attachment URL is not configured.")
                
                async with httpx.AsyncClient() as vapiclient:
                    attach_response = await vapiclient.post(attach_url, json=attach_payload, headers=get_headers())
                    attach_data = attach_response.json()
                    print(attach_data)
                    if attach_response.status_code in [200, 201]:
                        vapi_phone_uuid = attach_data.get("id")
                        purchased_entry = await PurchasedNumber.create(
                            user=user,
                            company = company,
                            phone_number=purchased_number.phone_number,
                            vapi_phone_uuid=vapi_phone_uuid,
                            friendly_name=purchased_number.friendly_name,
                            region=None, 
                            postal_code=None,
                            iso_country=None,
                        )
                        purchased_numbers.append(purchased_entry.phone_number)
            

    
            
            return {
                "success": True,
                "detail": f"Phone numbers {', '.join(purchased_numbers)} purchased and saved successfully!",
                "purchased_numbers": purchased_numbers,
                "sendedNumber": request.phone_number,
            }

    except Exception as e:
        error_message = str(e) 
        raise HTTPException(status_code=400, detail={"error": error_message})



@twilio_router.post("/remove-phone-number")
async def return_phone_number(request: RemoveNumberRequest, user: Annotated[User, Depends(get_current_user)]):
    try:
        purchased_number = client.incoming_phone_numbers.list(phone_number=request.phone_number)
        
        if not purchased_number:
           return {
           "success": False,
           "detail": f"Phone number {request.phone_number} was not found or has already been returned."
                }
        number_to_return = purchased_number[0]

        number_to_return.delete()

   
        await PurchasedNumber.filter(phone_number=number_to_return.phone_number).delete()

        return {
            "success": True,
            "detail": f"Phone number {number_to_return.phone_number} has been returned successfully!"
        }

    except Exception as e:
        error_message = str(e)
        raise HTTPException(status_code=400, detail={"error": error_message})

@twilio_router.get("/purchased_numbers")
async def get_purchased_numbers(current: Annotated[User, Depends(get_current_user)]):
    user, company = current
    purchased_numbers = await PurchasedNumber.filter(company = company).prefetch_related("user__company")

    if not purchased_numbers:
        return {"message": "No purchased numbers found."}

    return [
        {
            **dict(pn),
            "phone_number": pn.phone_number,
            "username": pn.user.name if pn.user else None,
            "email": pn.user.email if pn.user else None,
            "company_name": pn.user.company.company_name if pn.user and pn.user.company else None  
        }
        for pn in purchased_numbers
    ]





