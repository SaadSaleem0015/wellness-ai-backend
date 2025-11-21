import asyncio
import os
from datetime import timedelta, timezone
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends,HTTPException
import httpx
from helpers.jwt_token import get_current_user
from helpers.vapi_helper import generate_token, get_all_call_list, get_headers
import requests
from models.call_log import CallLog
from models.company import Company
from models.lead import Lead
from models.user import User
from datetime import datetime
from tortoise.expressions import Q
import asyncio
from datetime import datetime
from typing import Optional
import httpx
import requests
import os
from models.assistant import Assistant
from urllib.parse import quote

call_log_router = APIRouter()
token = generate_token()

   
@call_log_router.get("/all_call_logs")
async def get_logs(user: Annotated[User, Depends(get_current_user)]):
    return await CallLog.all()
    
@call_log_router.get("/user/call-logs") 
async def get_user_call_logs(user: Annotated[User, Depends(get_current_user)]
):
    try:
        call_logs = await CallLog.filter(company = user.company).prefetch_related("user").all()
        
        if not call_logs:
            return []

        return [{"id": log.id,
                 "call_id": log.call_id,
                 "call_started_at": log.call_started_at.isoformat() if log.call_started_at else None,
                 "call_ended_at": log.call_ended_at.isoformat() if log.call_ended_at else None,
                 "cost": str(log.cost) if log.cost else None,
                 "customer_number": log.customer_number,
                 "customer_name": log.customer_name,
                 "call_ended_reason": log.call_ended_reason,
                 "lead_id":log.lead_id
                } for log in call_logs]

    except Exception as e:
        print("An error occurred while retrieving call logs:")
        print(str(e))
        raise HTTPException(status_code=400, detail=f"{str(e)}")
    
@call_log_router.get("/user/call-logs-detail") 
async def get_user_call_logs(current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company  = current
        call_logs = await CallLog.filter(company=company).prefetch_related("user").all().order_by("-id")
        
        if not call_logs:  
            return []
        
        return call_logs

    except Exception as e:
        print("An error occurred while retrieving call logs:")
        print(str(e))
        raise HTTPException(status_code=400, detail=f"{str(e)}")
    
@call_log_router.get("/specific-number-call-logs/{phoneNumber}")
async def call_details(phoneNumber: str, user:Annotated[User, Depends(get_current_user)]):
    try:
        print("phoneNumber",phoneNumber)
        call_details = await CallLog.filter(user__company=user.company_id, customer_number = phoneNumber).all()
        if not call_details:
           return []
        return call_details
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{str(e)}")

@call_log_router.get("/user/call-logs") 
async def get_user_call_logs(user: Annotated[User, Depends(get_current_user)]
):
    try:
        call_logs = await CallLog.filter(company = user.company).prefetch_related("user").all()
        
        if not call_logs:
            return []
        
        return call_logs

    except Exception as e:
        print("An error occurred while retrieving call logs:")
        print(str(e))
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")
    

@call_log_router.get("/call/{call_id}")
async def get_call(call_id: str,user: Annotated[User, Depends(get_current_user)]):
    print("567898yui9")
    try:
        call_detail_url = f"https://api.vapi.ai/call/{call_id}" 
        response = requests.get(call_detail_url, headers=get_headers())
       
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to retrieve call details")

        call_data = response.json()
        
        started_at = call_data.get("startedAt", None)
        ended_at = call_data.get("endedAt", None)
        print("call started at ",started_at)
        print("call ended at ",ended_at)



        call_duration = None
        if started_at and ended_at:
            start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))

            call_duration = (end_time - start_time).total_seconds()
        important_info = {
            "recording_url": call_data.get("artifact", {}).get("recordingUrl", "N/A"),
            "transcript": call_data.get("artifact", {}).get("transcript", "No transcript available"),
            "ended_reason": call_data.get("endedReason", "Unknown"),
            "status": call_data.get("status", "Unknown"),
            "call_ended_at":call_data.get("endedAt", None),
            "call_started_at":call_data.get("startedAt", None),
            "cost": call_data.get("cost", 0),
            "created_at": call_data.get("createdAt", "Unknown"),
            "updated_at": call_data.get("updatedAt", "Unknown"),
            "call_duration": call_duration,  
            "assistant": {
                "id": call_data.get("assistantId", "Unknown"),
                "name": call_data.get("assistant", {}).get("name", "Unknown assistant"),
            },
            "variableValues": { 
                "name": call_data.get("assistantOverrides", {}).get("variableValues", {}).get("name", "Unknown"),
                "email": call_data.get("assistantOverrides", {}).get("variableValues", {}).get("email", "Unknown"),
                "mobile_no": call_data.get("assistantOverrides", {}).get("variableValues", {}).get("mobile_no", "Unknown"),
                "add_date": call_data.get("assistantOverrides", {}).get("variableValues", {}).get("add_date", "Unknown"),
                "custom_field_01": call_data.get("assistantOverrides", {}).get("variableValues", {}).get("custom_field_01", "Unknown"),
                "custom_field_02": call_data.get("assistantOverrides", {}).get("variableValues", {}).get("custom_field_02", "Unknown"),
            },
            # "successEvalution": success_evalution
        }
        # call = await CallLog.get_or_none(call_id = call_id)
        # # time_left = await TimeLimit.filter(user=user).first()
        # if call:
        #      call.call_ended_reason = call_data.get("endedReason", "Unknown")
        #      call.cost = call_data.get("cost", 0)
        #      call.status = call_data.get("status", "Unknown")
        #      call.call_duration = call_duration
        #      await call.save()
        # else:
        #     await CallLog.create(
        #      call_id=call_id,
        #      call_ended_reason=call_data.get("endedReason", "Unknown"),
        #      cost=call_data.get("cost", 0),
        #      status=call_data.get("status", "Unknown"),
        #  )
        
        # time_left.seconds = time_left.seconds - call_duration
        # await time_left.save()
                    
        return important_info

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

 
@call_log_router.delete("/call_log/{id}")
async def delete_calls(id:str):
    try:
        url = f"https://api.vapi.ai/call/{id}"
        headers = {
            "Authorization" :f"Bearer {token}"
        }
        response = requests.request("DELETE", url, headers=headers)
        if response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"VAPI phone number detachment failed with status {response.status_code}: {response.text}"
                )
        await CallLog.filter(call_id=id).delete()
        return{"success":True, "detail" : "Call log delted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Error Fetching Call logs: {str(e)}")
    

@call_log_router.get("/update_calls")
async def update_call_logs_for_missing_details():
    try:        
        calls_to_update = await CallLog.filter(
            Q(call_ended_reason__isnull=True) | Q(call_duration__isnull=True)
        ).all()
        
        if not calls_to_update:
            print("No calls need to be updated.")
            return {"message": "No calls need to be updated."}
        
        updated_count = 0
        
        for call in calls_to_update:
            call_id = call.call_id
            print(f"Fetching details for call: {call_id}")
            
            call_detail_url = f"https://api.vapi.ai/call/{call_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(call_detail_url, headers=get_headers())
            
            if response.status_code != 200:
                print(f"Failed to retrieve details for call {call_id}, status code {response.status_code}")
                continue  
                
            call_data = response.json()
            started_at = call_data.get("startedAt", None)
            ended_at = call_data.get("endedAt", None)
            call_ended_reason = call_data.get("endedReason", "Unknown")
            cost = call_data.get("cost", 0)
            status = call_data.get("status", "Unknown")
            transcript = call_data.get("artifact", {}).get("transcript", "No transcript available")
            
            call_duration = None
            if started_at and ended_at:
                try:
                    start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                    call_duration = (end_time - start_time).total_seconds()
                except ValueError as date_error:
                    print(f"Error parsing dates for call {call_id}: {date_error}")
                    call_duration = 0
            
            call.call_ended_reason = call_ended_reason
            call.cost = cost
            call.status = status
            call.call_duration = call_duration if call_duration else 0
            
            if ended_at:
                try:
                    call.call_ended_at = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                except ValueError as date_error:
                    print(f"Error parsing end date for call {call_id}: {date_error}")
                    call.call_ended_at = None
            
            await call.save()
            updated_count += 1
            print(f"Successfully updated call {call_id}")
            
        return {"message": f"Successfully updated {updated_count} calls"}
        
    except Exception as e:
        print(f"Error in update_call_logs_for_missing_details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def get_call_details(call_id: str, delay: int ,user :User, company: Company,  lead_id : Optional[int] = None ,   ):
    print("background task-----------------------")
    try:
        print(f"Task will run after {delay}")
        await asyncio.sleep(delay)
        print(delay)
        call_detail_url = f"https://api.vapi.ai/call/{call_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(call_detail_url, headers=get_headers())
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to retrieve call details")

        call_data = response.json()
        started_at = call_data.get("startedAt", None)
        ended_at = call_data.get("endedAt", None)        
        transcript= call_data.get("artifact", {}).get("transcript", "No transcript available")
        
        user = await User.filter(id=user.id).first()
        
        is_transferred = False
        
       
        
    
        

        lead = await Lead.filter(id=lead_id).first()
       

        call_duration = None
        if started_at and ended_at:
            start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            call_duration = (end_time - start_time).total_seconds()

        call = await CallLog.get_or_none(call_id=call_id)
        if call:
            call.is_transferred = is_transferred
            call.call_ended_reason = call_data.get("endedReason", "Unknown")
            call.cost = call_data.get("cost", 0)
            call.status = call_data.get("status", "Unknown")
            call.call_duration = call_duration if call_duration else 0
            call.criteria_satisfied = is_transferred
            
            if isinstance(ended_at, str):
                call.call_ended_at = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            else:
                call.call_ended_at = ended_at
            await call.save()
        else:
            await CallLog.create(
                is_transferred = is_transferred,
                call_id=call_id,
                call_ended_reason=call_data.get("endedReason", "Unknown"),
                cost=call_data.get("cost", 0),
                status=call_data.get("status", "Unknown"),
                call_ended_at=datetime.fromisoformat(ended_at.replace("Z", "+00:00")) if isinstance(ended_at, str) else ended_at,
                call_duration=call_duration,
                criteria_satisfied = is_transferred,
                company = company,
                user= user

            )


    except Exception as e:
        print(f"Error in get_call_details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



    
#this will use for scheduler call details only as background task is only available in the context of FasApi and our scheduler is not in that so it is not support the background taks we use it through the asyncio and handle the call logs and update them 
async def get_call_detail(call_id: str, delay: int, user_id: int, lead_id: Optional[int] = None):
    """
    Async function to get call details after a delay
    This runs as an independent asyncio task
    """
    print(f"Starting background task for call_id: {call_id}, delay: {delay}s")
    
    try:
        # Wait for the specified delay
        await asyncio.sleep(delay)
        print(f"Processing call details for call_id: {call_id}")
        
        # Get call details from VAPI
        call_detail_url = f"https://api.vapi.ai/call/{call_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(call_detail_url, headers=get_headers())
        
        if response.status_code != 200:
            print(f"Failed to retrieve call details: {response.status_code} - {response.text}")
            return
        
        call_data = response.json()
        started_at = call_data.get("startedAt")
        ended_at = call_data.get("endedAt")
        transcript = call_data.get("artifact", {}).get("transcript", "No transcript available")
        
        
        user = await User.filter(id=user_id).first()
        if not user:
            print(f"User with id {user_id} not found")
            return
        
    
        
        transfer_result = {"isTransferred": False}
        try:
            if transcript and transcript != "No transcript available":
                print(f"Transfer analysis completed: {transfer_result}")
        except Exception as e:
            print(f"Transfer analysis failed: {str(e)}")
            # Continue with default value
        
      
        is_transferred = transfer_result.get("isTransferred", False)
   
                
               
        call_duration = 0
        if started_at and ended_at:
            try:
                start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                call_duration = (end_time - start_time).total_seconds()
                print(f"Call duration calculated: {call_duration} seconds")
            except Exception as e:
                print(f"Failed to calculate call duration: {str(e)}")
        
        try:
            call = await CallLog.get_or_none(call_id=call_id)
            
            if call:
                call.is_transferred = is_transferred
                call.call_ended_reason = call_data.get("endedReason", "Unknown")
                call.cost = call_data.get("cost", 0)
                call.status = call_data.get("status", "Unknown")
                call.call_duration = call_duration
                call.criteria_satisfied = is_transferred
                
                if ended_at:
                    if isinstance(ended_at, str):
                        call.call_ended_at = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                    else:
                        call.call_ended_at = ended_at
                
                await call.save()
                print(f"Call log updated for call_id: {call_id}")
            else:
                # Create new call log
                await CallLog.create(
                    is_transferred=is_transferred,
                    call_id=call_id,
                    call_ended_reason=call_data.get("endedReason", "Unknown"),
                    cost=call_data.get("cost", 0),
                    status=call_data.get("status", "Unknown"),
                    call_ended_at=datetime.fromisoformat(ended_at.replace("Z", "+00:00")) if isinstance(ended_at, str) and ended_at else None,
                    call_duration=call_duration,
                    criteria_satisfied=is_transferred
                )
                print(f"New call log created for call_id: {call_id}")
            
          
        except Exception as e:
            print(f"Failed to update call log: {str(e)}")
        
        print(f"Background task completed successfully for call_id: {call_id}")
    
    except asyncio.CancelledError:
        print(f"Background task cancelled for call_id: {call_id}")
        raise
    except Exception as e:
        print(f"Unexpected error in background task for call_id {call_id}: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")


def create_background_task(call_id: str, delay: int, user_id: int, lead_id: Optional[int] = None):
    """
    Creates an asyncio task with proper error handling
    Returns the task so it can be tracked if needed
    """
    async def task_wrapper():
        try:
            await get_call_detail(call_id, delay, user_id, lead_id)
        except Exception as e:
            print(f"Background task failed for call_id {call_id}: {str(e)}")
    
    task = asyncio.create_task(task_wrapper())
    print(f"Background task created for call_id: {call_id}")
    return task



def normalize_timestamp(dt):
    dt = dt.astimezone(timezone.utc)
    # force milliseconds only (3 digits)
    iso = dt.isoformat(timespec="milliseconds")
    return iso.replace("+00:00", "Z")

@call_log_router.get("/calls-logs")
async def update_call_list(current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company = current

        # Get the last saved call log
        last_call_log = await CallLog.exclude(call_started_at=None).order_by("-call_started_at").first()
        print("last_call_log.call_started_at", last_call_log.call_started_at if last_call_log else None)

        # Determine createdAtGt
        if last_call_log and last_call_log.call_started_at:
            createdAtGt_raw = normalize_timestamp(last_call_log.call_started_at)
        else:
            # fallback: 14 days ago
            dt_14_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
            createdAtGt_raw = normalize_timestamp(dt_14_days_ago)

        createdAtGt = quote(createdAtGt_raw, safe='')
        print("createdAtGt:", createdAtGt)

        # Fetch from VAPI
        response = await get_all_call_list(createdAtGt)
        return response
        for call_data in response:

            # Only save inbound/outbound phone calls
            if call_data.get("type") not in ["inboundPhoneCall", "outboundPhoneCall"]:
                continue

            # Skip if exists
            existing_entry = await CallLog.filter(call_id=call_data["id"]).first()
            if existing_entry:
                continue

            try:
                assistant = await Assistant.filter(
                    vapi_assistant_id=call_data.get("assistantId")
                ).first().prefetch_related("user", "company")

                if not assistant:
                    continue

                user_obj = assistant.user
                company_obj = getattr(assistant, "company", None)

                # Timestamps
                started_at = call_data.get("startedAt")
                ended_at = call_data.get("endedAt")

                if not ended_at:  
                    continue

                # Duration
                call_duration = None
                if started_at and ended_at:
                    start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                    call_duration = (end_time - start_time).total_seconds()

                # Customer fields
                customer_info = call_data.get("customer") or {}
                customer_number = customer_info.get("number")
                customer_name = customer_info.get("name")

                # Save log
                await CallLog.create(
                    call_id=call_data.get("id"),
                    user=user_obj,
                    company=company_obj,
                    lead_id=None,
                    call_started_at=started_at,
                    call_ended_at=ended_at,
                    call_duration=call_duration,
                    customer_number=customer_number,
                    customer_name=customer_name,
                    cost=call_data.get("cost"),
                    status=call_data.get("status"),
                    call_ended_reason=call_data.get("endedReason"),
                    is_transferred=False,
                    criteria_satisfied=False,
                    type=call_data.get("type"),
                    recording_url=call_data.get("recordingUrl"),
                    transcript=call_data.get("transcript"),
                )

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error saving data: {str(e)}")

        # Return list
        call_logs = await CallLog.filter(company=company).prefetch_related("user").all()
        if not call_logs:
            return []

        return [{
            "id": log.id,
            "call_id": log.call_id,
            "call_started_at": log.call_started_at.isoformat() if log.call_started_at else None,
            "call_ended_at": log.call_ended_at.isoformat() if log.call_ended_at else None,
            "cost": str(log.cost) if log.cost else None,
            "customer_number": log.customer_number,
            "customer_name": log.customer_name,
            "call_ended_reason": log.call_ended_reason,
            "lead_id": log.lead_id,
            "type": log.type,
        } for log in call_logs]

    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")
