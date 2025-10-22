

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from tortoise.models import Model
from tortoise import fields
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel
import os
import hmac
import hashlib
import base64
import requests

CLIENT_ID = "q8osl-4rkawpoBa2AjzPmCjuRGxjJKsMfur09Kdba_I"
CLIENT_SECRET = "xxaaoTrovv5kA6m7pgDmDV7PQa_xwqAxlIztdz5-NG4"
WEBHOOK_KEY = "XCMgY5ymwGHoZ9CHLLuXboM1FqljG2TEdk9sZWeTFJc"
REDIRECT_URI = "http://localhost:8000/api/booking/oauth/callback"  
CALENDLY_AUTH_URL = "https://auth.calendly.com/oauth/authorize"
CALENDLY_TOKEN_URL = "https://auth.calendly.com/oauth/token"
CALENDLY_BASE_URL = "https://api.calendly.com"

booking_router = APIRouter(prefix="/booking", tags=["booking"])

class CalendlyToken(Model):
    id = fields.IntField(pk=True)
    access_token = fields.CharField(max_length=255)
    refresh_token = fields.CharField(max_length=255)
    expires_at = fields.DatetimeField() 

async def get_access_token():
    token = await CalendlyToken.first()
    if not token:
        raise HTTPException(status_code=401, detail="No token found. Authorize via /oauth/login first.")
    
    if token.expires_at < datetime.utcnow():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CALENDLY_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token.refresh_token,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                },
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Token refresh failed.")
            data = response.json()
            token.access_token = data["access_token"]
            token.refresh_token = data.get("refresh_token", token.refresh_token) 
            token.expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])
            await token.save()
    
    return token.access_token

@booking_router.get("/oauth/login")
async def oauth_login():
    url = "https://auth.calendly.com/oauth/authorize"
    querystring = {"response_type":"code","redirect_uri":"http://localhost:8000/api/booking/oauth/callback","code_challenge_method":"S256"}
    headers = {"Content-Type": "application/json"}

    response = requests.request("GET", url, headers=headers, params=querystring)
    print("response", response.text)
    # return RedirectResponse(auth_url)

# OAuth Callback: Exchange code for token and save
@booking_router.get("/oauth/callback")
async def oauth_callback(code: str):
    # Encode credentials for Basic Auth
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    print("credentials", credentials)
    auth_header = f"Basic {base64.b64encode(credentials.encode('utf-8')).decode('utf-8')}"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            CALENDLY_TOKEN_URL,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                # Add "code_verifier": "<your_verifier>" if using PKCE
            },
        )
        if response.status_code != 200:
            error_data = response.json()
            raise HTTPException(status_code=401, detail=f"OAuth failed: {error_data}")
        data = response.json()
        token, _ = await CalendlyToken.get_or_create(id=1)  # Single row
        token.access_token = data["access_token"]
        token.refresh_token = data["refresh_token"]
        token.expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])
        await token.save()
    return {"message": "OAuth successful. Token stored."}

class AvailabilityRequest(BaseModel):
    event_type_uri: str 
    days: int = 1  

@booking_router.post("/availability")
async def check_availability(req: AvailabilityRequest, token: str = Depends(get_access_token)):
    now = datetime.utcnow()
    start_time = (now + timedelta(days=req.days - 1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
    end_time = (now + timedelta(days=req.days)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CALENDLY_BASE_URL}/event_type_available_times",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "event_type": req.event_type_uri,
                "start_time": start_time,
                "end_time": end_time,
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        slots = data.get("collection", [])
        return {"available_slots": slots}

# Model for booking request
class BookingRequest(BaseModel):
    event_type_uri: str
    name: str
    email: str
    phone: str  # Not pre-filled, but can store/send SMS
    selected_date: str  # YYYY-MM-DD for pre-fill

# Create scheduling link for booking (during call: generate and return pre-filled URL)
@booking_router.post("/book")
async def book_appointment(req: BookingRequest, token: str = Depends(get_access_token)):
    # Create single-use scheduling link
    print("comes in")
    async with httpx.AsyncClient() as client:
        print("req" , req)
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
        print("booking_url", booking_url)
        # Pre-fill URL
        prefilled_url = f"{booking_url}?name={req.name.replace(' ', '%20')}&email={req.email}&date={req.selected_date}"
        # Here, you can integrate Twilio to send SMS with prefilled_url to req.phone
        print("prefilled_url", prefilled_url)
        
        return {"booking_url": prefilled_url, "message": "Send this link to patient for confirmation."}

# Cancel appointment
@booking_router.post("/cancel/{event_uuid}")
async def cancel_appointment(event_uuid: str, token: str = Depends(get_access_token)):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CALENDLY_BASE_URL}/scheduled_events/{event_uuid}/cancellation",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "Canceled via AI agent"},  # Optional
        )
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        return {"message": "Appointment canceled."}

# Model for reschedule (cancel old, create new link)
class RescheduleRequest(BookingRequest):
    old_event_uuid: str

# Reschedule: Cancel old and generate new link
@booking_router.post("/reschedule")
async def reschedule_appointment(req: RescheduleRequest, token: str = Depends(get_access_token)):
    # Cancel old
    await cancel_appointment(req.old_event_uuid, token)
    
    # Generate new link (reuse book logic)
    new_booking = await book_appointment(BookingRequest(**req.dict(exclude={"old_event_uuid"})), token)
    return {"message": "Rescheduled. New booking URL:", **new_booking}

# Webhook endpoint (optional, but since key provided)
@booking_router.post("/webhook")
async def calendly_webhook(request: Request, response: Response):
    # Verify signature
    signature = request.headers.get("Calendly-Webhook-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature.")
    
    timestamp, sig = signature.split(",")
    timestamp = timestamp.split("=")[1]
    sig = sig.split("=")[1]
    
    payload = await request.body()
    message = f"{timestamp}.{payload.decode()}"
    expected_sig = hmac.new(WEBHOOK_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    expected_sig_base64 = base64.b64encode(bytes.fromhex(expected_sig)).decode()
    
    if not hmac.compare_digest(sig, expected_sig_base64):
        raise HTTPException(status_code=401, detail="Invalid signature.")
    
    data = await request.json()
    # Handle event, e.g., if data["event"] == "invitee.created", log or process
    # For now, just acknowledge
    return {"message": "Webhook received."}