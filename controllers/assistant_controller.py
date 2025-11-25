from datetime import date, datetime
from typing import Annotated, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
import httpx
import pytz
from controllers.call_controller import get_call_details
from models.assistant import Assistant
from models.call_log import CallLog
from models.lead import Lead
from models.purchased_number import PurchasedNumber
from helpers.vapi_helper import create_query_tool, create_vapi_tool, user_add_payload,get_headers,generate_token
from helpers.email import send_off_hours_contact_email
from models.user import User
import os
import dotenv
import requests
from pydantic import BaseModel,EmailStr, Field
import os
import httpx
from helpers.jwt_token import get_current_user

dotenv.load_dotenv()
assistant_router = APIRouter()
header = get_headers()
token = generate_token()


class PhoneCallRequest(BaseModel):
    api_key: str
    first_name: str
    email: EmailStr
    number: str
    agent_id:Optional[str] = None

class AssistantCreate(BaseModel):
    name: str
    provider: str
    first_message: str
    model: str
    systemPrompt: str
    leadsfile : Optional[List[int]] = []
    temperature: float
    maxTokens: int
    transcribe_provider: str
    transcribe_language: str
    transcribe_model: str
    forwardingPhoneNumber: Optional[str] = None
    endCallPhrases: Optional[List[str]] = []
    voice_provider: str
    voice: str
    voice_model:str
    attached_Number: Optional[str] =None
    tools: Optional[List] = None


class DataForCall(BaseModel):
  first_name: str
  last_name: str
  email: str
  add_date: str
  mobile_no: str
  custom_field_01: Optional[str] = None
  custom_field_02: Optional[str] = None



class AttachNumberRequest(BaseModel):
    phone_number: str
    assistant_id: int


class OffHoursContact(BaseModel):
    patient_name: str = Field(..., min_length=1)
    email: EmailStr
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    message: Optional[str] = Field(None, max_length=1000)


 
@assistant_router.post("/assistants")
async def create_assistant(assistant_data: AssistantCreate, current: User = Depends(get_current_user)):
    try:
        user, company  = current
        required_fields = [
            'name', 'provider', 'first_message', 'model',
            'systemPrompt', 'temperature',
            'maxTokens', 'transcribe_provider',
            'transcribe_language', 'transcribe_model', 'voice_provider', 'voice',
        ]
        empty_fields = [field for field in required_fields if not getattr(assistant_data, field, None)]
        if empty_fields:
            raise HTTPException(status_code=400, detail=f"All fields are required. Empty fields: {', '.join(empty_fields)}")
        payload_data =await user_add_payload(assistant_data,user)
        
        headers = get_headers()  
        url = "https://api.vapi.ai/assistant"  
        response = requests.post(url=url, json=payload_data, headers=headers)  

        if response.status_code in [200, 201]:
          
            vapi_response_data = response.json()
            vapi_assistant_id = vapi_response_data.get('id')
            
            existing_assistants = await Assistant.filter(user=user).all().count()
            assistant_toggle = existing_assistants == 0

            new_assistant = await Assistant.create(
                user=user,
                company =company,
                name=assistant_data.name,
                provider=assistant_data.provider,
                first_message=assistant_data.first_message,
                model=assistant_data.model,
                systemPrompt=assistant_data.systemPrompt,
                leadsfile = assistant_data.leadsfile,
                temperature=assistant_data.temperature,
                maxTokens=assistant_data.maxTokens,
                transcribe_provider=assistant_data.transcribe_provider,
                transcribe_language=assistant_data.transcribe_language,
                transcribe_model=assistant_data.transcribe_model,
                voice_provider=assistant_data.voice_provider,
                forwardingPhoneNumber=assistant_data.forwardingPhoneNumber,
                endCallPhrases=assistant_data.endCallPhrases,
                voice=assistant_data.voice,
                vapi_assistant_id=vapi_assistant_id,
                attached_Number=assistant_data.attached_Number,
                assistant_toggle = assistant_toggle,
                voice_model = assistant_data.voice_model,
                tools = assistant_data.tools
            )
          

            if assistant_data.attached_Number:
                new_phonenumber = await PurchasedNumber.filter(phone_number = assistant_data.attached_Number).first()
                new_number_uuid = new_phonenumber.vapi_phone_uuid
                # requests.patch(
                # f"https://api.vapi.ai/phone-number/{new_number_uuid}",
                # json={"assistantId": vapi_assistant_id},
                # headers=headers
                # ).raise_for_status()
                
                new_assistant.attached_Number = assistant_data.attached_Number
                new_assistant.vapi_phone_uuid = new_number_uuid
              
                await new_assistant.save()
                return {
                        "success": True,
                        "id": new_assistant.id,
                        "name": new_assistant.name,
                        "detail": "Assistant created and phone number attached successfully."
                    }
             
           
           
            await new_assistant.save()
            
            return {
                "success": True,
                "id": new_assistant.id,
                "name": new_assistant.name,
                "detail": "Assistant created successfully."
            }

        else:
            vapi_error = response.json()
            error_message = vapi_error.get("message", ["An unknown error occurred"])
            for message in error_message:
                if "forwardingPhoneNumber" in message:
                    raise HTTPException(status_code=400, detail="ForwardingPhoneNumber must be a valid phone number in the E.164 format.")
            
            raise HTTPException(status_code=response.status_code, detail=f"VAPI Error: {response.text}")

    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        print(f"Exception occurred: {e}")
        raise HTTPException(status_code=400, detail=f"An error occurred while creating the assistant: {str(e)}")





@assistant_router.get("/get-user-assistants")
async def get_all_assistants(current: Annotated[User, Depends(get_current_user)]):

    try:
        user, company  = current
        assistants = await Assistant.filter(company=company).all().order_by("id")
        if not assistants:
            return []

        return assistants
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{str(e)}")
    
@assistant_router.get("/get-assistant/{assistant_id}")
async def get_assistant(assistant_id: int,current: Annotated[User, Depends(get_current_user)]):
    try:
         user, company  = current
         assistant = await Assistant.get(id=assistant_id)
         if not assistant:
             return []
         return assistant
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{e}")
    
@assistant_router.delete("/assistants/{assistant_id}")
async def delete_assistant(assistant_id: int, current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company  = current
        assistant = await Assistant.get_or_none(id=assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail="Assistant not found")
        
        # if assistant.vapi_phone_uuid:
        #     requests.patch(
        #         f"https://api.vapi.ai/phone-number/{assistant.vapi_phone_uuid}",
        #         json={"assistantId": None},
        #         headers=get_headers()
        #     ).raise_for_status()
        
        
 
        vapi_assistant_id = assistant.vapi_assistant_id
        vapi_url = f"{os.environ['VAPI_URL']}/assistant/{vapi_assistant_id}"
        response = requests.delete(vapi_url, headers=get_headers())

        if response.status_code in [200, 201]:
            await assistant.delete()
            return {
                "success": True,
                "detail": "Assistant has been deleted."
            }
        else:
            raise HTTPException(status_code=400, detail=f"VAPI delete failed with status {response.status_code}: {response.text}")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{e}")

@assistant_router.put("/update_assistant/{assistant_id}")
async def update_assistant(assistant_id: str, assistant: AssistantCreate, current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company  = current
        existing_assistant = await Assistant.get_or_none(id=assistant_id)
        if not existing_assistant:
            raise HTTPException(status_code=404, detail='Assistant not found')

        # Build payload via same helper used in create
        payload_data = await user_add_payload(assistant, user)

        vapi_assistant_id = existing_assistant.vapi_assistant_id
        vapi_url = f"{os.environ.get('VAPI_URL')}/assistant/{vapi_assistant_id}"
        
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(vapi_url, json=payload_data, headers=get_headers())
            print("-----------", response)
            if response.status_code not in [200, 201]:
                    vapi_error = response.json()
                    error_messages = vapi_error.get("message", ["An unknown error occurred"])
                    for message in error_messages:
                        if "forwardingPhoneNumber" in message:
                            raise HTTPException(
                                status_code=400,
                                detail="ForwardingPhoneNumber must be a valid phone number in the E.164 format. "
                            )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"VAPI update failed: {', '.join(error_messages)}"
                    )
            
            if assistant.attached_Number:
                new_phonenumber = await PurchasedNumber.filter(phone_number=assistant.attached_Number).first()
                if new_phonenumber:
                    new_number_uuid = new_phonenumber.vapi_phone_uuid
                    new_phonenumber.attached_assistant = existing_assistant.id
                    await new_phonenumber.save()
                    existing_assistant.attached_Number = assistant.attached_Number
                    existing_assistant.vapi_phone_uuid = new_number_uuid
                    await existing_assistant.save()
           
        # Persist updated assistant fields mirroring create
        existing_assistant.name = assistant.name
        existing_assistant.provider = assistant.provider
        existing_assistant.first_message = assistant.first_message
        existing_assistant.model = assistant.model
        existing_assistant.systemPrompt = assistant.systemPrompt
        existing_assistant.temperature = assistant.temperature
        existing_assistant.maxTokens = assistant.maxTokens
        existing_assistant.transcribe_provider = assistant.transcribe_provider
        existing_assistant.transcribe_language = assistant.transcribe_language
        existing_assistant.transcribe_model = assistant.transcribe_model
        existing_assistant.voice_provider = assistant.voice_provider
        existing_assistant.voice = assistant.voice
        existing_assistant.forwardingPhoneNumber = assistant.forwardingPhoneNumber
        existing_assistant.endCallPhrases = assistant.endCallPhrases
        existing_assistant.leadsfile = assistant.leadsfile
        existing_assistant.voice_model = assistant.voice_model
        existing_assistant.tools = assistant.tools
        await existing_assistant.save()
    

        return {
            "success": True,
            "id": existing_assistant.id,
            "name": existing_assistant.name,
            "detail": "Assistant updated successfully."
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Exception occurred: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")
  
# @assistant_router.post("/attach-number-to-assistant")
# async def attach_number_to_assistant(request: AttachNumberRequest, current: User = Depends(get_current_user)):
#     try:
#         user, company  = current
#         assistant = await Assistant.get(id=request.assistant_id, user=user)
#         phonenumber = await PurchasedNumber.get(phone_number=request.phone_number)
#         if not assistant:
#             raise HTTPException(status_code=404, detail="Assistant not found")

#         requests.patch(
#             f"https://api.vapi.ai/phone-number/{phonenumber.vapi_phone_uuid}",
#             json={"assistantId": assistant.vapi_assistant_id},
#             headers=get_headers()
#         ).raise_for_status()
        
#         assistant.attached_Number = request.phone_number
#         assistant.vapi_phone_uuid = phonenumber.vapi_phone_uuid
#         phonenumber.attached_assistant = assistant.id
#         await assistant.save()
#         await phonenumber.save()

  
#         return {
#             "success": True,
#             "detail": f"Phone number {request.phone_number} attached successfully to assistant {assistant.name}",
#             "attached_assistant": assistant.id
#         }

#     except Exception as e:
#         print(str(e))
#         raise HTTPException(status_code=400, detail=f"An error occurred: {e}")
    


# @assistant_router.post("/detach-number-from-assistant")
# async def detach_number_from_assistant(request: AttachNumberRequest, current: User = Depends(get_current_user)):
#     try:
#         user, company  = current

#         phonenumber = await PurchasedNumber.get(phone_number=request.phone_number)
#         assistants = await Assistant.filter(user=user, attached_Number=phonenumber.phone_number).all()

#         if not assistants:
#             raise HTTPException(status_code=404, detail="No assistants found using this phone number")

#         requests.patch(
#             f"https://api.vapi.ai/phone-number/{phonenumber.vapi_phone_uuid}",
#             json={"assistantId": None},
#             headers=get_headers()
#         ).raise_for_status()
#         for assistant in assistants:
#             assistant.attached_Number = None
#             assistant.vapi_phone_uuid = None
#             await assistant.save()
           

#         phonenumber.attached_assistant = None
#         await phonenumber.save()

#         return {
#             "success": True,
#             "detail": f"Phone number {request.phone_number} detached successfully from {len(assistants)} assistant(s)"
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"An error occurred: {e}")

@assistant_router.post("/assistant-call/{vapi_assistant_id}/{lead_id}")
async def assistant_call(
    vapi_assistant_id: str,
    lead_id: int,
    current: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks 
):
    try:
        user, company  = current

        assistant = await Assistant.get_or_none(vapi_assistant_id=vapi_assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail="Assistant not found")

        lead = await Lead.get_or_none(id=lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
      

        mobile_no = lead.phone if lead.phone.startswith('+') else f"+1{lead.phone}"

        
        if not assistant.attached_Number:
            return {"success": False, "detail": "Unable to call! No Number Attached with this Assistant"}
        
        phone_number  = await PurchasedNumber.filter(phone_number = assistant.attached_Number).first()
        

      
        # call_max_duration = call_max_duration if call_max_duration > 150 else 150
        # print(f"the max call duration is {call_max_duration}")
        
       
        
        call_url = "https://api.vapi.ai/call"
        payload = {
            "name": "From AIBC",
            "assistantId": assistant.vapi_assistant_id,
            "customer": {
                "numberE164CheckEnabled": True,
                "extension": None,
                "number": mobile_no,
            },
            "phoneNumberId": phone_number.vapi_phone_uuid,
            "assistantOverrides": {
                "variableValues": {
                    "first_name": lead.name,
                    "email": lead.email,
                    "mobile_no": mobile_no,
                    "add_date": lead.add_date.isoformat() if isinstance(lead.add_date, (date, datetime)) else None,
                },
                # "maxDurationSeconds": call_max_duration
            }
        }


         
        response = requests.post(call_url, json=payload, headers=get_headers())

        if response.status_code in [200, 201]:
          
            vapi_response_data = response.json()
            call_id = vapi_response_data.get("id")
            started_at = vapi_response_data.get("createdAt")
            first_name = vapi_response_data.get("assistantOverrides", {}).get("variableValues", {}).get("first_name")
            last_name = vapi_response_data.get("assistantOverrides", {}).get("variableValues", {}).get("last_name")
            customer_name = f"{first_name} {last_name}"  
            customer_number = lead.phone

            if not call_id:
                raise HTTPException(status_code=400, detail="No callId found in the VAPI response.")

            new_call_log = CallLog(
                user=user,
                company = company,
                call_id=call_id,
                call_started_at=started_at,
                customer_name=customer_name,
                customer_number=customer_number,
                lead_id=lead_id
            )
            await new_call_log.save()

            background_tasks.add_task(get_call_details, call_id=call_id, delay=400 , lead_id = lead_id , user_id =user.id)

            return {
                "success": True,
                "detail": "Call initiated successfully",
                "vapi_response": vapi_response_data
            }

        else:
          vapi_error = response.json()
          error_message = vapi_error.get("message", ["An unknown error occurred"])

          for message in error_message:
                if "customer.number" in message:
                    concise_error = (
                        "The customer's phone number is invalid. "
                        "Please ensure it is in the correct E.164 format with the country code (e.g., US: +1)."
                    )
                    return {"success": False, "detail": concise_error}

                elif "phoneNumber.fallbackDestination.number" in message:
                    concise_error = (
                        "The fallback destination phone number is invalid. "
                        "Ensure it is in E.164 format, including the country code."
                    )
                    return {"success": False, "detail": concise_error}

          return {
                "success": False,
                "detail": vapi_error.get("message", "An unknown error occurred.")
            }

    except Exception as e:
        print(f"Error occurred in assistant_call: {repr(e)}")
        raise HTTPException(status_code=400, detail=f" {repr(e)}")


@assistant_router.post("/phone-call/{vapi_assistant_id}/{number}")
async def assistant_call(
    vapi_assistant_id: str,
    number: str,  
    data: DataForCall,
    current: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
):
    try:
        user, company  = current
        
       

        mobile_no = number if number.startswith('+') else f"+1{number}"
        # call_max_duration = call_max_duration if call_max_duration >150 else 150
        
        call_url = "https://api.vapi.ai/call"
        
        payload = {
            "name": "From wellness",
            "assistantId": vapi_assistant_id,
            "customer": {
                "numberE164CheckEnabled": True,
                "extension": None,
                "number": mobile_no,
            },
            "phoneNumberId": "4ec91e52-ea1d-4c3d-844c-06bd64e27942",
            "assistantOverrides": {
                "variableValues": {
                    "first_name": data.first_name,
                    "last_name": data.last_name,
                    "email": data.email,
                    "mobile_no": mobile_no,
                    "add_date": data.add_date.isoformat() if isinstance(data.add_date, (date, datetime)) else None,
                },
                # "maxDurationSeconds": call_max_duration
            },
        }
        
        response = requests.post(call_url, json=payload, headers=get_headers())  

        if response.status_code in [200, 201]:
            response_data = response.json()

            call_id = response_data.get("id")
            started_at = response_data.get("createdAt")
            first_name = response_data.get("assistantOverrides", {}).get("variableValues", {}).get("first_name")
            last_name = response_data.get("assistantOverrides", {}).get("variableValues", {}).get("last_name")
            customer_name = f"{first_name} {last_name}" if first_name and last_name else "Unknown"
            customer_number = mobile_no
            
            if not call_id:
                raise HTTPException(status_code=400, detail="No callId found in the VAPI response.")

            new_call_log = CallLog(
                user=user,
                company = company,
                call_id=call_id,
                call_started_at=started_at,
                customer_name=customer_name,
                customer_number=customer_number,
            )
            await new_call_log.save()

            background_tasks.add_task(get_call_details, call_id=call_id, delay=400, user=user, company=company)

            return {
                "success": True,
                "detail": "Call initiated successfully",
                "vapi_response": response_data,
            }

        else:
            error_data = response.json()
            error_message = error_data.get("message", ["An unknown error occurred"])

            if "Twilio Error" in error_message and "Perhaps you need to enable some international permissions" in error_message:
                return {
                    "success": False,
                    "detail": (
                        "Couldn't create the Twilio call. Your account may not be authorized to make international calls to this number. "
                    ),
                }

            for message in error_message:
                if "customer.number" in message:
                    return {
                        "success": False,
                        "detail": (
                            "The customer's phone number is invalid. "
                            "Please ensure it is in the correct E.164 format with the country code (e.g., US: +1)."
                        ),
                    }
                elif "phoneNumber.fallbackDestination.number" in message:
                    return {
                        "success": False,
                        "detail": (
                            "The fallback destination phone number is invalid. "
                            "Ensure it is in E.164 format, including the country code."
                        ),
                    }

            return {"success": False, "detail": error_data.get("message", "An unknown error occurred.")}

    except Exception as e:
        print(f"Error occurred in assistant_call: {repr(e)}")
        raise HTTPException(status_code=400, detail=f"Error occurred: {repr(e)}")


@assistant_router.get("/check-clinic-hours")
async def check_clinic_hours():
    try:
        pst = pytz.timezone("America/Los_Angeles")
        now_pst = datetime.now(pst)
    
        weekday = now_pst.weekday()  
        hour = now_pst.hour         

        if weekday == 6:
            return {
                "allowed": False,
                "reason": "Clinic is closed (Sunday)"
            }
        
        if hour < 9 or hour >= 17:
            return {
                "allowed": False,
                "reason": "Clinic is closed (Outside 9 AM–5 PM PST)"
            }

        return {
            "allowed": True,
            "reason": "Inside working hours"
        }

    except Exception as e:
        print("Error checking clinic hours:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@assistant_router.post("/off-hours-contact")
async def notify_off_hours_contact(contact: OffHoursContact):
    try:
        email_sent = send_off_hours_contact_email(
            patient_name=contact.patient_name,
            patient_email=contact.email,
            phone=contact.phone,
            note=contact.message,
        )

        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to notify the clinic.")

        return {"success": True, "detail": "Clinic has been notified."}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Email configuration error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to send notification: {e}")