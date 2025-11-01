import asyncio
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request, Response
import httpx
from pydantic import BaseModel, Field
from datetime import datetime, timedelta , timezone
import os
import hmac
import hashlib
import base64
from urllib.parse import urlparse, parse_qs, urlencode
import pytz
from helpers.email import send_booking_confirmation_email
from models.availablityblock import AvailabilityBlock
from models.patient import Patient
from models.appointment import Appointment, AppointmentStatus
class PatientInfoRequest(BaseModel):
    phone: str
    # email: str

CALENDLY_PAT = os.getenv("CALENDLY_PAT")
if not CALENDLY_PAT:
    raise ValueError("CALENDLY_PAT not set in environment")

CALENDLY_BASE_URL = "https://api.calendly.com"
WEBHOOK_KEY = os.getenv("CALENDLY_WEBHOOK_KEY", "XCMgY5ymwGHoZ9CHLLuXboM1FqljG2TEdk9sZWeTFJc")  # Optional, from env if set

booking_router = APIRouter(prefix="/booking", tags=["booking"])

async def get_access_token():
    if not CALENDLY_PAT:
        raise HTTPException(status_code=401, detail="No PAT configured.")
    return CALENDLY_PAT
async def get_blocked_slots_from_db(date: str) -> set[str]:
    record = await AvailabilityBlock.get_or_none(date=date)
    print("record--------------------", record)
    if record is None:
        return set()
    blocked_list = record.blocked_slots  
    print(f"✅ DEBUG: blocked_list={blocked_list[:3]}... (type={type(blocked_list)})")
    return set(blocked_list)

@booking_router.get("/test-token")
async def test_token(token: str = Depends(get_access_token)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CALENDLY_BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return {"user": response.json()["resource"], "message": "PAT is working!"}

@booking_router.get("/event_types")
async def list_event_types(token: str = Depends(get_access_token)):
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            f"{CALENDLY_BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=user_response.status_code, detail=user_response.text)
        user_uri = user_response.json()["resource"]["uri"]
        
        response = await client.get(
            f"{CALENDLY_BASE_URL}/event_types",
            headers={"Authorization": f"Bearer {token}"},
            params={"user": user_uri}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

class AvailabilityRequest(BaseModel):
    event_type_uri: str  
    days: int = 1 

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

@booking_router.post("/availability")
async def check_availability(req: AvailabilityRequest, token: str = Depends(get_access_token)):
    if not req.event_type_uri.startswith("https://api.calendly.com/event_types/"):
        raise HTTPException(
            status_code=400, 
            detail="event_type_uri must be a full URI (e.g., https://api.calendly.com/event_types/{uuid})"
        )

    async with httpx.AsyncClient() as client:
        # Get Calendly user
        user_response = await client.get(
            f"{CALENDLY_BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=user_response.status_code, detail=user_response.text)
        user_uri = user_response.json()["resource"]["uri"]

        # Current time in Pacific Time
        now_pacific = datetime.now(PACIFIC_TZ)

        # Map days to target date
        if req.days == 1:
            # Today: Start from max(current time, 9 AM PDT)
            target_date = now_pacific
            start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            if start_time_pacific < now_pacific:
                minutes = (now_pacific.minute // 15 + 1) * 15
                start_time_pacific = now_pacific.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)
                if start_time_pacific < now_pacific:
                    start_time_pacific += timedelta(minutes=15)
            end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
        elif req.days == 2:
            # Tomorrow: Start at 9 AM PDT
            target_date = now_pacific + timedelta(days=1)
            start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
        elif req.days == 3:
            # Day after tomorrow: Start at 9 AM PDT
            target_date = now_pacific + timedelta(days=2)
            start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
        elif req.days == 4:
            # Day after tomorrow: Start at 9 AM PDT
            target_date = now_pacific + timedelta(days=3)
            start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
        elif req.days == 5:
            # Day after tomorrow: Start at 9 AM PDT
            target_date = now_pacific + timedelta(days=4)
            start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
        else:
            raise HTTPException(status_code=400, detail="days must be 1 (today), 2 (tomorrow), or 3 (day after tomorrow)")

        # Convert to UTC for Calendly API
        start_time_utc = start_time_pacific.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
        end_time_utc = end_time_pacific.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")

        # Fetch available times
        response = await client.get(
            f"{CALENDLY_BASE_URL}/event_type_available_times",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "event_type": req.event_type_uri,
                "start_time": start_time_utc,
                "end_time": end_time_utc,
                "user": user_uri
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())

        data = response.json()
        slots = data.get("collection", [])
        for slot in slots:
            print(f"Raw slot: {slot['start_time']}")

        converted_slots = []
        date_str = target_date.strftime("%Y-%m-%d")
        blocked_set = await get_blocked_slots_from_db(date_str)
        for slot in slots:
            utc_dt = datetime.fromisoformat(slot["start_time"].replace("Z", "+00:00"))
            pacific_dt = utc_dt.astimezone(PACIFIC_TZ)
            slot_start_time = pacific_dt.strftime("%Y-%m-%dT%H:%M:%S%z")

            if req.days == 1 and pacific_dt < now_pacific:
                continue

            if pacific_dt < start_time_pacific or pacific_dt > end_time_pacific:
                continue

            scheduling_url = slot["scheduling_url"]
            parsed_url = urlparse(scheduling_url)
            path_parts = parsed_url.path.split('/')
            timestamp_str = path_parts[-1]
            try:
                utc_dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            pacific_dt = utc_dt.astimezone(PACIFIC_TZ)
            pacific_timestamp = pacific_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
            path_parts[-1] = pacific_timestamp
            new_path = '/'.join(path_parts)
            new_scheduling_url = parsed_url._replace(path=new_path).geturl()
            slot["scheduling_url"] = new_scheduling_url
            slot["start_time"] = slot_start_time
            slot_time = pacific_dt.strftime("%H:%M")  # "10:00"
            if slot_time in blocked_set:
                continue
            converted_slots.append(slot)

        return {
            "available_slots": converted_slots,
            "timezone": "America/Los_Angeles",
            "start_time": start_time_pacific.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "end_time": end_time_pacific.strftime("%Y-%m-%dT%H:%M:%S%z")
        }
# @booking_router.post("/availability")
# async def check_availability(req: AvailabilityRequest, token: str = Depends(get_access_token)):
#     print("----------------")
#     if not req.event_type_uri.startswith("https://api.calendly.com/event_types/"):
#         raise HTTPException(
#             status_code=400, 
#             detail="event_type_uri must be a full URI (e.g., https://api.calendly.com/event_types/{uuid})"
#         )

#     async with httpx.AsyncClient() as client:
#         # Get Calendly user
#         user_response = await client.get(
#             f"{CALENDLY_BASE_URL}/users/me",
#             headers={"Authorization": f"Bearer {token}"}
#         )
#         if user_response.status_code != 200:
#             raise HTTPException(status_code=user_response.status_code, detail=user_response.text)
#         user_uri = user_response.json()["resource"]["uri"]

#         # Current time in Pacific Time
#         now_pacific = datetime.now(PACIFIC_TZ)

#         # Map days to target date
#         if req.days == 1:
#             # Today: Start from max(current time, 9 AM PDT)
#             target_date = now_pacific
#             start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
#             if start_time_pacific < now_pacific:
#                 minutes = (now_pacific.minute // 15 + 1) * 15
#                 start_time_pacific = now_pacific.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)
#                 if start_time_pacific < now_pacific:
#                     start_time_pacific += timedelta(minutes=15)
#             end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
#         elif req.days == 2:
#             # Tomorrow: Start at 9 AM PDT
#             target_date = now_pacific + timedelta(days=1)
#             start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
#             end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
#         elif req.days == 3:
#             # Day after tomorrow: Start at 9 AM PDT
#             target_date = now_pacific + timedelta(days=2)
#             start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
#             end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
#         elif req.days == 4:
#             # Day after tomorrow: Start at 9 AM PDT
#             target_date = now_pacific + timedelta(days=3)
#             start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
#             end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
#         elif req.days == 5:
#             # Day after tomorrow: Start at 9 AM PDT
#             target_date = now_pacific + timedelta(days=4)
#             start_time_pacific = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
#             end_time_pacific = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
#         else:
#             raise HTTPException(status_code=400, detail="days must be 1 (today), 2 (tomorrow), or 3 (day after tomorrow)")

#         # Convert to UTC for Calendly API
#         start_time_utc = start_time_pacific.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
#         end_time_utc = end_time_pacific.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")

#         # Fetch available times
#         response = await client.get(
#             f"{CALENDLY_BASE_URL}/event_type_available_times",
#             headers={"Authorization": f"Bearer {token}"},
#             params={
#                 "event_type": req.event_type_uri,
#                 "start_time": start_time_utc,
#                 "end_time": end_time_utc,
#                 "user": user_uri
#             },
#         )
#         if response.status_code != 200:
#             raise HTTPException(status_code=response.status_code, detail=response.json())

#         data = response.json()
#         slots = data.get("collection", [])
#         for slot in slots:
#             print(f"Raw slot: {slot['start_time']}")

#         converted_slots = []
#         for slot in slots:
#             utc_dt = datetime.fromisoformat(slot["start_time"].replace("Z", "+00:00"))
#             pacific_dt = utc_dt.astimezone(PACIFIC_TZ)
#             slot_start_time = pacific_dt.strftime("%Y-%m-%dT%H:%M:%S%z")

#             if req.days == 1 and pacific_dt < now_pacific:
#                 print(f"Skipping past slot: {slot_start_time}")
#                 continue

#             if pacific_dt < start_time_pacific or pacific_dt > end_time_pacific:
#                 print(f"Skipping slot outside target window: {slot_start_time}")
#                 continue

#             # Convert scheduling_url timestamp to Pacific Time
#             scheduling_url = slot["scheduling_url"]
#             parsed_url = urlparse(scheduling_url)
#             path_parts = parsed_url.path.split('/')
#             timestamp_str = path_parts[-1]
#             try:
#                 utc_dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
#             except ValueError:
#                 print(f"Invalid timestamp in scheduling_url: {timestamp_str}")
#                 continue
#             pacific_dt = utc_dt.astimezone(PACIFIC_TZ)
#             pacific_timestamp = pacific_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
#             path_parts[-1] = pacific_timestamp
#             new_path = '/'.join(path_parts)
#             new_scheduling_url = parsed_url._replace(path=new_path).geturl()
#             slot["scheduling_url"] = new_scheduling_url
#             slot["start_time"] = slot_start_time

#             converted_slots.append(slot)
#             print(f"Included slot: {slot_start_time}")

#         return {
#             "available_slots": converted_slots,
#             "timezone": "America/Los_Angeles",
#             "start_time": start_time_pacific.strftime("%Y-%m-%dT%H:%M:%S%z"),
#             "end_time": end_time_pacific.strftime("%Y-%m-%dT%H:%M:%S%z")
#         }
class AppointmentBookingRequest(BaseModel):
    event_type_uri: str
    name: str
    email: str
    phone: str  
    selected_date: str  #
    selected_slot_url : str

class BookingRequest(BaseModel):
    event_type_uri: str
    name: str
    email: str
    phone: str  
    selected_date: str  

@booking_router.post("/book")
async def book_appointment(req: BookingRequest, token: str = Depends(get_access_token)):
    patient, created = await Patient.get_or_create(
        phone=req.phone,
        defaults={
            "name": req.name,
            "email": req.email
        }
    )
    print("4", req.event_type_uri)
    
    async with httpx.AsyncClient() as client:
        link_response = await client.post(
            f"{CALENDLY_BASE_URL}/scheduling_links",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "max_event_count": 1,
                "owner": req.event_type_uri,
                "owner_type": "EventType",
            },
        )
        if link_response.status_code != 201:
            raise HTTPException(status_code=link_response.status_code, detail=link_response.json())
        booking_url = link_response.json()["resource"]["booking_url"]
        query = urlencode({
            "name": req.name,
            "email": req.email,
            "date": req.selected_date,
        })
        prefilled_url = f"{booking_url}/{req.selected_date}?{query}"
        print(prefilled_url)
        try:
            send_booking_confirmation_email(req.email, req.name, prefilled_url)
        except Exception as e:
            print("Email send failed:", e)
        
        return {
            "booking_url": prefilled_url, 
            "message": "Send this link to patient for confirmation.",
            "patient_id": patient.id,
            "patient_created": created
        }

class CancelAppointmentRequest(BaseModel):
    event_uuid: str
@booking_router.post("/cancel")
async def cancel_appointment(request: CancelAppointmentRequest, token: str = Depends(get_access_token)):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CALENDLY_BASE_URL}/scheduled_events/{request.event_uuid}/cancellation",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "Canceled via AI agent"}, 
        )
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        return {"message": "Appointment canceled."}

class RescheduleRequest(BaseModel):
    event_uuid: str
    event_type_uri: str
    phone: str  
    new_date: str 

async def cancel_previous_appointment(event_uuid:str, token: str = Depends(get_access_token)):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CALENDLY_BASE_URL}/scheduled_events/{event_uuid}/cancellation",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "Canceled via AI agent"}, 
        )
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        return {"message": "Appointment canceled."}

@booking_router.post("/reschedule")
async def reschedule_appointment(req: RescheduleRequest, token: str = Depends(get_access_token)):
    try:

        await cancel_previous_appointment(req.event_uuid, token)
        
        patient = await Patient.filter(phone=req.phone).first()
        

        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found for the given phone number.")
        
        payload = {
            "event_type_uri": req.event_type_uri,
            "name": patient.name,
            "email": patient.email,
            "phone": req.phone,
            "selected_date": req.new_date
        }
        
        
        new_booking = await book_appointment(BookingRequest(**payload), token)
        
        return {"message": "Rescheduled successfully.", **new_booking}

    except HTTPException as e:
        raise e

    except Exception as e:
        print("❌ Error while rescheduling appointment:", str(e))
        raise HTTPException(status_code=500, detail="An error occurred while rescheduling the appointment.")

@booking_router.post("/webhook")
async def calendly_webhook(request: Request, response: Response):
    signature = request.headers.get("Calendly-Webhook-Signature")
    if WEBHOOK_KEY and signature:
        try:
            timestamp, sig = signature.split(",")
            timestamp = timestamp.split("=")[1]
            sig = sig.split("=")[1]
            
            payload = await request.body()
            message = f"{timestamp}.{payload.decode()}"
            expected_sig = hmac.new(WEBHOOK_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
            expected_sig_base64 = base64.b64encode(bytes.fromhex(expected_sig)).decode()
            
            if not hmac.compare_digest(sig, expected_sig_base64):
                raise HTTPException(status_code=401, detail="Invalid signature.")
        except Exception:
            raise HTTPException(status_code=401, detail="Signature verification failed.")
    
    data = await request.json()
    return {"message": "Webhook received and processed."}

# Optional: Get scheduled events (list upcoming bookings) - Fixed to include user param
# @booking_router.get("/scheduled_events")
# async def list_scheduled_events_with_invitees(
#     token: str = Depends(get_access_token), 
#     status: str = "active"
# ):
#     async with httpx.AsyncClient() as client:
#         # Get current user URI (unchanged)
#         user_response = await client.get(
#             f"{CALENDLY_BASE_URL}/users/me",
#             headers={"Authorization": f"Bearer {token}"}
#         )
#         if user_response.status_code != 200:
#             raise HTTPException(status_code=user_response.status_code, detail=user_response.text)
#         user_uri = user_response.json()["resource"]["uri"]
        
#         # Get list of events (unchanged, but removed count=100 for default pagination; add page_token if needed)
#         response = await client.get(
#             f"{CALENDLY_BASE_URL}/scheduled_events",
#             headers={"Authorization": f"Bearer {token}"},
#             params={"status": status, "user": user_uri}
#         )
#         if response.status_code != 200:
#             raise HTTPException(status_code=response.status_code, detail=response.text)
        
#         events_data = response.json()["collection"]
        
#         # Parallel fetch invitees for each event
#         async def fetch_invitees(event: Dict) -> Dict:
#             uuid = event["uri"].split("/")[-1]  # Extract UUID from uri
#             invitees_resp = await client.get(
#                 f"{CALENDLY_BASE_URL}/scheduled_events/{uuid}/invitees",
#                 headers={"Authorization": f"Bearer {token}"}
#             )
#             if invitees_resp.status_code == 200:
#                 invitees = invitees_resp.json()["collection"]  # Array of invitees
#                 event["event_guests"] = invitees  # Merge into event
#             else:
#                 event["event_guests"] = []  # Fallback if error (e.g., no invitees)
#                 # Optionally log: print(f"Error fetching invitees for {uuid}: {invitees_resp.text}")
#             return event
        
#         # Run in parallel
#         updated_events = await asyncio.gather(*[fetch_invitees(event) for event in events_data])
        
#         # Return with pagination intact
#         return {
#             "collection": updated_events,
#             "pagination": response.json()["pagination"]
#         }

@booking_router.get("/scheduled_events")
async def get_patient_appointments(
    token: str = Depends(get_access_token), 
    status: str = "active"  
):
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            f"{CALENDLY_BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=user_response.status_code, detail=user_response.text)
        user_uri = user_response.json()["resource"]["uri"]
        
        response = await client.get(
            f"{CALENDLY_BASE_URL}/scheduled_events",
            headers={"Authorization": f"Bearer {token}"},
            params={"user": user_uri}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        events_data = response.json()["collection"]
        
        async def process_event(event: Dict) -> Dict:
            uuid = event["uri"].split("/")[-1]
            start_time_str = event["start_time"]
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            is_past = start_time < now
            
            invitees_resp = await client.get(
                f"{CALENDLY_BASE_URL}/scheduled_events/{uuid}/invitees",
                headers={"Authorization": f"Bearer {token}"}
            )
            invitees = []
            if invitees_resp.status_code == 200:
                invitees = invitees_resp.json()["collection"]
            
            if not invitees:  
                return None
            
            invitee = invitees[0]  
            
            patient_data = {
                "name": invitee.get("name", "Unknown"),
                "email": invitee.get("email", "Unknown"),
                "appointment_date": start_time_str,  
                "questions_answers": [
                {"question": qa["question"], "answer": qa["answer"]}
                for qa in invitee.get("questions_and_answers", [])
            ],

                "status": event["status"]
            }
            
            if is_past:
                cancel_resp = await client.post(
                    f"{CALENDLY_BASE_URL}/scheduled_events/{uuid}/cancel",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"canceled_by": "System (past appointment cleanup)"}
                )
                if cancel_resp.status_code == 200:
                    patient_data["status"] = "canceled"
                    patient_data["cancel_url"] = "N/A (auto-canceled)"
                else:
                    patient_data["cancel_url"] = f"Error canceling: {cancel_resp.text}"
            else:
                cancel_url_resp = await client.post(
                    f"{CALENDLY_BASE_URL}/scheduled_events/{uuid}/cancel_with_url",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"text": "If you need to reschedule or cancel, click below."}
                )
                if cancel_url_resp.status_code == 200:
                    patient_data["cancel_url"] = cancel_url_resp.json().get("cancel_url", "Error generating")
                else:
                    patient_data["cancel_url"] = f"Error: {cancel_url_resp.text}"
            
            return patient_data
        
        # Process in parallel
        results = await asyncio.gather(*[process_event(event) for event in events_data])
        filtered_results = [r for r in results if r]  
        return {"appointments": filtered_results}


@booking_router.get("/appointments")
async def list_appointments(
    token: str = Depends(get_access_token), 
    status: str = "active"
):
    async with httpx.AsyncClient() as client:
        # Get user URI
        user_response = await client.get(
            f"{CALENDLY_BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=user_response.status_code, detail=user_response.text)
        user_uri = user_response.json()["resource"]["uri"]
        
        # Get events list
        response = await client.get(
            f"{CALENDLY_BASE_URL}/scheduled_events",
            headers={"Authorization": f"Bearer {token}"},
            params={"user": user_uri}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        events_data = response.json()["collection"]
        
        async def process_and_save_appointment(event: Dict) -> Dict:
            uuid = event["uri"].split("/")[-1]
            invitees_resp = await client.get(
                f"{CALENDLY_BASE_URL}/scheduled_events/{uuid}/invitees",
                headers={"Authorization": f"Bearer {token}"}
            )
            invitees = []
            if invitees_resp.status_code == 200:
                invitees = invitees_resp.json()["collection"]
            
            if not invitees:
                return None
            
            invitee = invitees[0]  # Assume single invitee
            appointment_date = datetime.fromisoformat(event["start_time"].replace("Z", "+00:00"))
            
            # Check if appointment already exists with same UUID and status
            existing_appointment = await Appointment.filter(uuid=uuid).first()
            
            if existing_appointment and existing_appointment.status.value == event["status"]:
                # Skip saving if same UUID and status already exists
                return {
                    "uuid": uuid,
                    "name": invitee.get("name", "Unknown"),
                    "email": invitee.get("email", "Unknown"),
                    "appointment_date": event["start_time"],
                    "status": event["status"],
                    "saved": False,
                    "reason": "Already exists with same status"
                }
            
            # Get or create patient by email/phone
            patient_email = invitee.get("email", "")
            patient_name = invitee.get("name", "Unknown")
            
            # Try to find patient by email first, then by phone if available
            patient = await Patient.filter(email=patient_email).first()
            if not patient and "phone" in invitee:
                patient = await Patient.filter(phone=invitee["phone"]).first()
            
            if not patient:
                # Create new patient if not found
                patient = await Patient.create(
                    name=patient_name,
                    email=patient_email,
                    phone=invitee.get("phone", "")
                )
            else:
                # Update patient info if changed
                if patient.name != patient_name or patient.email != patient_email:
                    patient.name = patient_name
                    patient.email = patient_email
                    if "phone" in invitee and patient.phone != invitee["phone"]:
                        patient.phone = invitee["phone"]
                    await patient.save()
            
            # Create or update appointment
            appointment_data = {
                "patient": patient,
                "event_type_uri": event.get("event_type", ""),
                "appointment_date": appointment_date,
                "status": AppointmentStatus(event["status"]),
                "questions_answers": [
                    {"question": qa["question"], "answer": qa["answer"]}
                    for qa in invitee.get("questions_and_answers", [])
                ]
            }
            
            if existing_appointment:
                # Update existing appointment
                for key, value in appointment_data.items():
                    setattr(existing_appointment, key, value)
                await existing_appointment.save()
                appointment = existing_appointment
            else:
                # Create new appointment
                appointment = await Appointment.create(
                    uuid=uuid,
                    **appointment_data
                )
            
            return {
                "uuid": uuid,
                "name": invitee.get("name", "Unknown"),
                "email": invitee.get("email", "Unknown"),
                "appointment_date": event["start_time"],
                "status": event["status"],
                "saved": True,
                "appointment_id": appointment.id,
                "patient_id": patient.id
            }
        
        results = await asyncio.gather(*[process_and_save_appointment(event) for event in events_data])
        filtered_results = [r for r in results if r]
        
        return {"appointments": filtered_results}

@booking_router.get("/appointments/db")
async def get_appointments_from_db(
    status: str = "active",
    limit: int = 100,
    offset: int = 0
):
    """Get appointments directly from database"""
    # Convert status string to enum
    try:
        status_enum = AppointmentStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Query appointments with patient info
    appointments = await Appointment.filter(
        status=status_enum
    ).prefetch_related('patient').offset(offset).limit(limit).all()
    
    result = []
    for appointment in appointments:
        result.append({
            "id": appointment.id,
            "uuid": appointment.uuid,
            "patient_name": appointment.patient.name,
            "patient_email": appointment.patient.email,
            "patient_phone": appointment.patient.phone,
            "appointment_date": appointment.appointment_date.isoformat(),
            "status": appointment.status.value,
            "event_type_uri": appointment.event_type_uri,
            "questions_answers": appointment.questions_answers,
            "cancel_url": appointment.cancel_url,
            "created_at": appointment.created_at.isoformat(),
            "updated_at": appointment.updated_at.isoformat()
        })
    
    return {"appointments": result, "total": len(result)}

@booking_router.get("/patients")
async def get_patients(
    limit: int = 100,
    offset: int = 0
):
    """Get patients from database"""
    patients = await Patient.all().offset(offset).limit(limit)
    
    result = []
    for patient in patients:
        # Get appointment count for each patient
        appointment_count = await Appointment.filter(patient=patient).count()
        
        result.append({
            "id": patient.id,
            "name": patient.name,
            "email": patient.email,
            "phone": patient.phone,
            "appointment_count": appointment_count,
            "created_at": patient.created_at.isoformat(),
            "updated_at": patient.updated_at.isoformat()
        })
    
    return {"patients": result, "total": len(result)}

@booking_router.get("/patients/{patient_id}/appointments")
async def get_patient_appointments(
    patient_id: int,
    status: str = "active"
):
    """Get appointments for a specific patient"""
    try:
        status_enum = AppointmentStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    patient = await Patient.get_or_none(id=patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    appointments = await Appointment.filter(
        patient=patient,
        status=status_enum
    ).order_by('-appointment_date').all()
    
    result = []
    for appointment in appointments:
        result.append({
            "id": appointment.id,
            "uuid": appointment.uuid,
            "appointment_date": appointment.appointment_date.isoformat(),
            "status": appointment.status.value,
            "event_type_uri": appointment.event_type_uri,
            "questions_answers": appointment.questions_answers,
            "cancel_url": appointment.cancel_url,
            "created_at": appointment.created_at.isoformat()
        })
    
    return {
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "email": patient.email,
            "phone": patient.phone
        },
        "appointments": result
    }

@booking_router.post("/patient-info")
async def get_patient_appointments_by_phone(
    request: PatientInfoRequest,
):
    """Get appointments for a patient by phone number"""
    
    print("request", request)
    # Find patient by phone number
    patient = await Patient.filter(phone=request.phone).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient with phone number {request.phone} not found")
    
    # Get appointments for this patient
    appointments = await Appointment.filter(
        patient=patient,
    ).order_by('-appointment_date').all()
    
    result = []
    for appointment in appointments:
        result.append({
            "id": appointment.id,
            "uuid": appointment.uuid,
            "appointment_date": appointment.appointment_date.isoformat(),
            "status": appointment.status.value,
            "event_type_uri": appointment.event_type_uri,
            "questions_answers": appointment.questions_answers,
            "cancel_url": appointment.cancel_url,
            "created_at": appointment.created_at.isoformat()
        })
    
    return {
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "email": patient.email,
            "phone": patient.phone
        },
        "appointments": result,
        "total_appointments": len(result)
    }

@booking_router.get("/appointments/{uuid}")
async def get_appointment_detail(
    uuid: str,
    token: str = Depends(get_access_token)
):
    async with httpx.AsyncClient() as client:
        # Get user URI (for consistency)
        user_response = await client.get(
            f"{CALENDLY_BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=user_response.status_code, detail=user_response.text)
        user_uri = user_response.json()["resource"]["uri"]
        
        # Get single event details
        event_resp = await client.get(
            f"{CALENDLY_BASE_URL}/scheduled_events/{uuid}",
            headers={"Authorization": f"Bearer {token}"},
            params={"user": user_uri}
        )
        if event_resp.status_code != 200:
            raise HTTPException(status_code=event_resp.status_code, detail=event_resp.text)
        event = event_resp.json()["resource"]
        
        start_time_str = event["start_time"]
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        is_past = start_time < now
        
        invitees_resp = await client.get(
            f"{CALENDLY_BASE_URL}/scheduled_events/{uuid}/invitees",
            headers={"Authorization": f"Bearer {token}"}
        )
        invitees = []
        if invitees_resp.status_code == 200:
            invitees = invitees_resp.json()["collection"]
        
        if not invitees:
            raise HTTPException(status_code=404, detail="No invitees found for this appointment")
        
        invitee = invitees[0] 
        
        patient_data = {
            "name": invitee.get("name", "Unknown"),
            "email": invitee.get("email", "Unknown"),
            "appointment_date": start_time_str,
            "questions_answers": [
                {"question": qa["question"], "answer": qa["response"]}
                for qa in invitee.get("answers", [])
            ],
            "status": event["status"],
            "cancel_url": invitee.get("cancel_url", "N/A")  # Extract directly!
        }
        
        # if is_past:
        #     cancel_resp = await client.post(
        #         f"{CALENDLY_BASE_URL}/scheduled_events/{uuid}/cancel",
        #         headers={"Authorization": f"Bearer {token}"},
        #         json={"canceled_by": "System (past appointment cleanup)"}
        #     )
        #     if cancel_resp.status_code == 200:
        #         patient_data["status"] = "canceled"
        #         patient_data["cancel_url"] = "N/A (auto-canceled)"
        #     else:
        #         patient_data["cancel_url"] = f"Error canceling: {cancel_resp.text}"
        
        return patient_data









class UpdateSlotRequest(BaseModel):
    date: str          # "2025-01-05"
    slot: str          # "14:30"
    action: str   

@booking_router.post("/update-slot")
async def update_slot(req: UpdateSlotRequest):
    if req.action not in ["block", "unblock"]:
        raise HTTPException(status_code=400, detail="action must be add or remove")
    try:
        datetime.strptime(req.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be YYYY-MM-DD")

    record = await AvailabilityBlock.get_or_none(date=req.date)

    if not record:
        record = await AvailabilityBlock.create(date=req.date, blocked_slots=[])

    blocked = set(record.blocked_slots) if record.blocked_slots else set()

    if req.action == "block":
        blocked.add(req.slot)
    elif req.action == "unblock":
        blocked.discard(req.slot)

    record.blocked_slots = list(blocked)
    await record.save()

    return {
        "message": "Updated successfully",
        "date": req.date,
        "blocked_slots": record.blocked_slots
    }


@booking_router.get("/blocked/{date}")
async def get_blocked_slots(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be YYYY-MM-DD")

    record = await AvailabilityBlock.get_or_none(date=date)

    return {
        "date": date,
        "blocked_slots": record.blocked_slots if record else []
    }
