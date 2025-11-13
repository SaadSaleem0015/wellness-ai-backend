
#             "history": history,
#         }) # type: ignore
        
        
#         print("Full agent response:", response)
#         ai_message = ""
#         if "messages" in response and response["messages"]:
#             last_msg = response["messages"][-1]
#             if hasattr(last_msg, "content"):
#                 ai_message = last_msg.content
#             elif isinstance(last_msg, dict):
#                 ai_message = last_msg.get("content", "")
        
#         print("Agent response:", ai_message)
#         return ai_message
#     except Exception as e:
#         return f"Error: {str(e)}"


from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Literal, Optional
from os import environ
import asyncio
import httpx
from datetime import datetime

# Define input schemas for booking tools
class CheckAvailabilityInput(BaseModel):
    event_type_uri: str = Field(description="Calendly event type URI for the treatment")
    preferred_date: str = Field(description="Give preferred date in form like # Format: 'YYYY-MM-DD'  e.g., 2025-11-10 if user say today then today date if  tomorrow then tomorrow date do this plz")

class BookAppointmentInput(BaseModel):
    event_type_uri: str = Field(description="Calendly event type URI for the treatment")
    name: str = Field(description="Patient's full name")
    email: str = Field(description="Patient's email address")
    phone: str = Field(description="Patient's phone number with country code")
    selected_date: str = Field(description="Selected appointment date is the date that is the start time provided by the availability tool do not change the format")

class RescheduleAppointmentInput(BaseModel):
    event_uuid: str = Field(description="UUID of the appointment to reschedule")
    event_type_uri: str = Field(description="Calendly event type URI for the treatment")
    phone: str = Field(description="Patient's phone number with country code")
    new_date: str = Field(description="New appointment date in format: 2025-10-23T23:30:00Z")

class CancelAppointmentInput(BaseModel):
    event_uuid: str = Field(description="UUID of the appointment to cancel")

class GetPatientInfoInput(BaseModel):
    phone: str = Field(description="Patient's phone number with country code")

# Your FastAPI base URL - adjust as needed
FASTAPI_BASE_URL = "http://localhost:8000/api"  # Change to your actual URL
CALENDLY_PAT = environ.get("CALENDLY_PAT")

# Define the booking tools
@tool(args_schema=CheckAvailabilityInput)
async def check_availability_tool(event_type_uri: str, preferred_date: str) -> str:
    """Check available appointment slots for a specific treatment type and date."""
    try:
        print(f"Checking availability for {event_type_uri} on {preferred_date}")
        
        # Convert preferred_date to days parameter for your API
        # target_date = datetime.fromisoformat(preferred_date.replace('Z', '+00:00'))
        # today = datetime.now().date()
        # days_diff = (target_date.date() - today).days + 1
        
        # if int(preferred_date) < 1 or int(preferred_date) > 5:
        #     return "Error: Can only check availability for next 5 days"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_BASE_URL}/booking/availability",
                json={
                    "event_type_uri": event_type_uri,
                    "date": preferred_date
                },
                headers={"Authorization": f"Bearer {CALENDLY_PAT}"} if CALENDLY_PAT else {}
            )
            
            if response.status_code == 200:
                result = response.json()
                slots = result.get("available_slots", [])
                print("the available slots are:",slots)
                if slots:
                    return f"Available slots: {slots}"
                else:
                    return "No available slots for the selected date."
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                return f"Error checking availability: {error_detail}"
                
    except Exception as e:
        print(f"Error in check_availability_tool: {str(e)}")
        return f"Error checking availability: {str(e)}"

@tool(args_schema=BookAppointmentInput)
async def book_appointment_tool(event_type_uri: str, name: str, email: str, phone: str, selected_date: str) -> str:
    """Book a new appointment for a patient."""
    try:
        print(f"Booking appointment for {name} ({email}) on {selected_date}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_BASE_URL}/booking/book",
                json={
                    "event_type_uri": event_type_uri,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "selected_date": selected_date
                },
                headers={"Authorization": f"Bearer {CALENDLY_PAT}"} if CALENDLY_PAT else {}
            )
            
            if response.status_code == 200:
                result = response.json()
                booking_url = result.get("booking_url", "No URL returned")
                return f"Appointment booked successfully! Booking URL: {booking_url}"
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                return f"Error booking appointment: {error_detail}"
                
    except Exception as e:
        print(f"Error in book_appointment_tool: {str(e)}")
        return f"Error booking appointment: {str(e)}"

@tool(args_schema=RescheduleAppointmentInput)
async def reschedule_appointment_tool(event_uuid: str, event_type_uri: str, phone: str, new_date: str) -> str:
    """Reschedule an existing appointment."""
    try:
        print(f"Rescheduling appointment {event_uuid} to {new_date}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_BASE_URL}/booking/reschedule",
                json={
                    "event_uuid": event_uuid,
                    "event_type_uri": event_type_uri,
                    "phone": phone,
                    "new_date": new_date
                },
                headers={"Authorization": f"Bearer {CALENDLY_PAT}"} if CALENDLY_PAT else {}
            )
            
            if response.status_code == 200:
                result = response.json()
                return f"Appointment rescheduled successfully: {result}"
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                return f"Error rescheduling appointment: {error_detail}"
                
    except Exception as e:
        print(f"Error in reschedule_appointment_tool: {str(e)}")
        return f"Error rescheduling appointment: {str(e)}"

@tool(args_schema=CancelAppointmentInput)
async def cancel_appointment_tool(event_uuid: str) -> str:
    """Cancel an existing appointment."""
    try:
        print(f"Canceling appointment {event_uuid}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_BASE_URL}/booking/cancel",
                json={
                    "event_uuid": event_uuid
                },
                headers={"Authorization": f"Bearer {CALENDLY_PAT}"} if CALENDLY_PAT else {}
            )
            
            if response.status_code == 200:
                result = response.json()
                return f"Appointment canceled successfully: {result}"
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                return f"Error canceling appointment: {error_detail}"
                
    except Exception as e:
        print(f"Error in cancel_appointment_tool: {str(e)}")
        return f"Error canceling appointment: {str(e)}"

@tool(args_schema=GetPatientInfoInput)
async def get_patient_info_tool(phone: str) -> str:
    """Get patient information and appointment history."""
    try:
        print(f"Getting patient info for phone: {phone}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_BASE_URL}/booking/patient-info",
                json={
                    "phone": phone
                },
                headers={"Authorization": f"Bearer {CALENDLY_PAT}"} if CALENDLY_PAT else {}
            )
            
            if response.status_code == 200:
                result = response.json()
                patient = result.get("patient", {})
                appointments = result.get("appointments", [])
                
                patient_info = f"Patient: {patient.get('name', 'N/A')} ({phone})"
                if appointments:
                    appointment_details = []
                    for appt in appointments:
                        status = appt.get('status', 'N/A')
                        date = appt.get('appointment_date', 'N/A')
                        appointment_details.append(f"{date} - {status}")
                    patient_info += f"\nAppointments: {', '.join(appointment_details)}"
                else:
                    patient_info += "\nNo appointments found."
                    
                return patient_info
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                return f"Error getting patient info: {error_detail}"
                
    except Exception as e:
        print(f"Error in get_patient_info_tool: {str(e)}")
        return f"Error getting patient info: {str(e)}"

# Define the weather input schema
class WeatherInput(BaseModel):
    """Input for weather queries."""
    location: str = Field(description="City name or coordinates")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="Temperature unit preference"
    )
    include_forecast: bool = Field(
        default=False,
        description="Include 5-day forecast"
    )



# Set up OpenAI API key
OPENAI_API_KEY = environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

# Initialize the model
model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    timeout=30,
    api_key=OPENAI_API_KEY
)

# Get current date
current_date = datetime.now().strftime("%Y-%m-%d")

# Create the agent with all tools
agent = create_agent(
    model,
    tools=[
        check_availability_tool,
        book_appointment_tool,
        reschedule_appointment_tool,
        cancel_appointment_tool,
        get_patient_info_tool
                ],
    system_prompt=f"""
# Renee - Wellness Diagnostics and Medispa AI Assistant
Today's date is {current_date}
🗓 Date Interpretation Rules:
- ALWAYS assume the user means a date in the current year: {current_date.split("-")[0]}.
- NEVER check or correct whether the date’s weekday matches the calendar.
- If a user provides a day name (e.g., Tuesday) and a date (e.g., 11/11) that conflict:
  - DO NOT mention the conflict.
  - Clarify by asking: “To confirm, you’d like their date at their time correct?”

## Identity & Purpose
You are Renee, the friendly and  assistant for Wellness Diagnostics and Medispa, under Dr. Gloria Tumbaga. You serve as the  receptionist, providing warm, patient-centered care through every interaction.
clinic is only open on monday and tuesday ask user to book only in these two days.
## Core Responsibilities
- Booking new appointments
- Rescheduling existing appointments
- Canceling appointments
- Confirming appointment details
- Answering general inquiries
- Providing weather information when relevant

## Communication Style
**Tone:** Warm, empathetic, professional, and reassuring
**Pace:** Conversational and thorough - provide complete information
**Behavior:** Always acknowledge user messages fully before responding. Be patient and detailed in explanations.

## Availability Display Behavior
- When the availability tool returns a list of available slots:
  - Only show the first (earliest) available slot to the user initially.
  - Say something like: “The first available time is 11:30 AM. Would you like to see more options?”
- If the user asks for “next”, “later”, “other”, “more”, “show more”, or anything similar:
  - Then show the next few available slots (2–3 at a time).
  - Continue revealing more in the same order each time they ask.
- Do NOT show all available slots at once unless the user explicitly says “show all” or “list all times”.
- When sending the chosen time to the `book_appointment_tool`, always use the exact ISO string (e.g., `2025-11-03T11:30:00-0800`) returned by the availability tool without reformatting.
- When displaying the time to the user, you may show it in a readable format (e.g., “11:30 AM”).



## Appointment Management Protocols

## Time Format and Booking Rules
- When displaying available slots to patients, you may show friendly readable times (e.g., “11:30 AM”).
- However, when calling or sending data to `book_appointment_tool`, you MUST always use the exact `start_time` value returned by the `check_availability_tool`.
- Do not alter, format, or convert this time string in any way before passing it to the booking tool.
- Example:
  - Shown to patient: “The available slot is 11:30 AM.”
  - Sent to booking tool: `"selected_date": "2025-11-03T11:30:00-0800"`
- All times remain in the USA Pacific Time Zone.



### 📋 New Patient Booking Flow
1. **Greeting**: Warm welcome and introduction
3. **Treatment Interest**: "What treatment are you interested in today?"
4. **Preferred Timing**: "Do you have a preferred day or time for your appointment?"
5. **Availability Check**: Use check_availability_tool with correct event_type_uri
6. **Slot Presentation**: 
   - "The earliest available time I see is [time]. Would that work for you?"
   - If declined, offer next available slot
7. **Confirmation**: Use book_appointment_tool once patient agrees

### 🔄 Rescheduling Flow
1. Verify identity: "May I have your phone number to look up your appointment?"
2. Confirm phone number
3. Use get_patient_info_tool to find active appointments
4. Check availability for new preferred time
5. Use reschedule_appointment_tool with new date

### ❌ Cancellation Flow
1. Verify identity with phone number
2. Confirm cancellation reason: "May I ask why you need to cancel?"
3. Use cancel_appointment_tool with event_uuid
4. Express understanding and offer to reschedule

### 📧 General Inquiry Handling
- Be knowledgeable about all services and treatments
- Provide clear, comprehensive information
- Offer to book appointments when appropriate
- Use get_weather tool if travel conditions are discussed

## Technical Specifications

### Event Type URIs
- New Patient Consultation: https://api.calendly.com/event_types/ABCLL2BT4KLAFTAW
- Neurotoxin Treatment: https://api.calendly.com/event_types/FGANO5ETSWQ44YBH
- Filler Treatment: https://api.calendly.com/event_types/f66f5285-a5b8-484b-ad2a-80824c0504b9
- Neurotoxins + Filler: https://api.calendly.com/event_types/834e3445-020f-411c-99c9-6cddb6266c6c
- Laser Hair Removal: https://api.calendly.com/event_types/3fcdb9ef-fad1-40b1-a180-779a3175bab6
- Advanced Laser: https://api.calendly.com/event_types/6ab5b561-ddae-497a-b5f7-4d2bb3422918
- Injection Follow-Up: https://api.calendly.com/event_types/f66f5285-a5b8-484b-ad2a-80824c0504b9

## Must give same time slots as provided by the availability tool. do not change the time format. when giving to booking tool use the exact time provided by availability tool.give time in USA pacific time zone.

### Confirmation Protocol
After successful booking/rescheduling:
"Perfect! You'll receive an email confirmation shortly. We look forward to seeing you at the clinic! Have a wonderful day!"

## Information Collection Best Practices
- Always confirm critical information (name, phone, email) before proceeding
- Provide clear summaries of collected information before finalizing
- Be transparent about what information is needed and why

## Error Handling
- If tools fail, reassure the user: "I'm having trouble accessing the system right now. Let me try that again for you."
- Never share technical error details with users
- Always have a fallback option (e.g., "Would you like me to have someone contact you via email?")

## Response Guidelines
- Provide complete, well-structured responses
- Use appropriate emojis to enhance warmth and clarity
- Break complex information into digestible parts
- Always end with clear next steps or questions

Remember: You are the first point of contact for patients. Your warmth, professionalism, and attention to detail set the tone for their entire experience with Wellness Diagnostics and Medispa.
"""
)

async def chat_with_agent(user_input: str, history: list[dict]) -> str:
    try:
        # Construct the full messages list including history
        messages = history[:] 
        messages.append({"role": "user", "content": user_input})
        
        response = await agent.ainvoke({
            "messages": messages,
            "history": history,
        }) # type: ignore
        
        # print("Full agent response:", response)
        ai_message = ""
        if "messages" in response and response["messages"]:
            last_msg = response["messages"][-1]
            if hasattr(last_msg, "content"):
                ai_message = last_msg.content
            elif isinstance(last_msg, dict):
                ai_message = last_msg.get("content", "")
        
        print("Agent response:", ai_message)
        return ai_message
    except Exception as e:
        return f"I apologize, but I'm experiencing some technical difficulties. Could you please try again in a moment? If the problem continues, feel free to call us directly at the clinic."