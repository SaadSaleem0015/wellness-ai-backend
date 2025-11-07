from fastapi import APIRouter,Depends,Request,Form,BackgroundTasks
from pydantic import BaseModel
from helpers.chat_chain import chat_with_agent
from models.chat import Chat
from models.chat_message import  ChatMessage
from helpers.jwt_token import get_current_user
from models.chat_setting import ChatSetting
from models.user import User
import os
from twilio.rest import Client




chatbotrouter = APIRouter()

class ChatRequest(BaseModel):
    message: str
    phone_number: str

class ChatSettingRequest(BaseModel):
    prompt: str
    model: str
    openai_key: str



@chatbotrouter.post("/chatbot/test")
async def chatbot_endpoint(request:ChatRequest):
    # try:
    #     data = await request.json()
    #     print(data)
    #     return {"message": "Message received","data": data}
    # except Exception as e:
        # print(e)
        # return {"message": "Error","data": e}
    chat = await Chat.get_or_none(phone_number=request.phone_number)
    try:
        if not chat:
            chat = Chat(phone_number=request.phone_number)
            await chat.save()
        history = []
        messages = await ChatMessage.filter(chat=chat).order_by("created_at")
        for msg in messages:
            history.append({"role": "user", "content": msg.message})
            history.append({"role": "assistant", "content": msg.answer})

        response_message = await chat_with_agent(request.message, history)
        chat_message = ChatMessage(
            chat=chat,
            message=request.message,
            answer=response_message
        )
        await chat_message.save()
        return {"response": response_message}
    except Exception as e:
        return {"error": str(e)}



# Twilio credentials (from your environment variables or directly)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

# Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Your Twilio phone number (the one that receives messages)
TWILIO_PHONE_NUMBER = "+19513875945"   # your number here

@chatbotrouter.post("/chatbot")
async def chatbot_endpoint(request: Request,background_tasks: BackgroundTasks):
    form_data = await request.form()
    from_number = form_data.get("From")     # Sender number
    incoming_message = form_data.get("Body")  # Message text
    
    chat = await Chat.filter(phone_number=from_number).first()
    if not chat:
        chat = await Chat.create(phone_number=from_number)

    try:
        # Twilio sends data as form-urlencoded, not JSON

        print(f"📩 Incoming from {from_number}: {incoming_message}")

        # Retrieve or create chat record

        # Build history
        history = []
        messages = await ChatMessage.filter(chat=chat).order_by("created_at")
        for msg in messages:
            history.append({"role": "user", "content": msg.message})
            history.append({"role": "assistant", "content": msg.answer})

        # Get AI response
        ai_response = await chat_with_agent(incoming_message, history)

        # Save chat message
        await ChatMessage.create(
            chat=chat,
            message=incoming_message,
            answer=ai_response
        )

        # Send message back via Twilio
        background_tasks.add_task(
            twilio_client.messages.create,
            body=ai_response,
            from_=TWILIO_PHONE_NUMBER,
            to=from_number
        )

        print(f"✅ Replied to {from_number}: {ai_response}")

        return {"status": "success", "response": ai_response}

    except Exception as e:
        print("❌ Error:", e)
        return {"status": "error", "message": str(e)}





@chatbotrouter.get("/chats/{phone_number}")
async def get_chat_history(phone_number: str,current: User = Depends(get_current_user)):
    chat = await Chat.get_or_none(phone_number=phone_number)
    if not chat:
        return {"history": []}
    messages = await ChatMessage.filter(chat=chat).order_by("created_at")
    history = []
    for msg in messages:
        history.append({
            "message": msg.message,
            "answer": msg.answer,
            "created_at": msg.created_at,
            "updated_at": msg.updated_at
        })
    return {"history": history}

@chatbotrouter.delete("/chats/{phone_number}")
async def delete_chat(phone_number: str,current: User = Depends(get_current_user)):
    chat = await Chat.get_or_none(phone_number=phone_number)
    if not chat:
        return {"message": "Chat not found"}
    await ChatMessage.filter(chat=chat).delete()
    await chat.delete()
    return {"message": "Chat deleted successfully"}

@chatbotrouter.get("/chats")
async def list_chats(current: User = Depends(get_current_user)):
    chats = await Chat.all().order_by("id")
    result = []
    for chat in chats:
        first_message = await ChatMessage.filter(chat=chat).order_by("created_at").first()
        result.append({
            "phone_number": chat.phone_number,
            "first_message": first_message.message if first_message else None,
            "first_answer": first_message.answer if first_message else None,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at
        })
    return result

@chatbotrouter.post("/settings")
async def chatbot_settings(
    prompt: str = Form(...),
    model: str = Form(...),
    openai_key: str = Form(...),
    current: User = Depends(get_current_user)
):
    settings = await ChatSetting.filter().first()
    if not settings:
        settings = ChatSetting(
            prompt=prompt,
            model=model,
            openai_key=openai_key
        )
        await settings.save()
    else:
        settings.prompt = prompt
        settings.model = model
        settings.openai_key = openai_key
        await settings.save()

    return {"success":True,"detail": "Settings updated successfully"}


@chatbotrouter.get("/settings")
async def get_chatbot_settings(current: User = Depends(get_current_user)):
    settings = await ChatSetting.filter().first()
    return {"settings": settings}

