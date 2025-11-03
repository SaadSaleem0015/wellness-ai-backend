from fastapi import APIRouter,Depends
from pydantic import BaseModel
from helpers.chat_chain import chat_with_agent
from models.chat import Chat
from models.chat_message import  ChatMessage
from helpers.jwt_token import get_current_user
from models.user import User



chatbotrouter = APIRouter()

class ChatRequest(BaseModel):
    message: str
    phone_number: str




@chatbotrouter.post("/chatbot")
async def chatbot_endpoint(request: ChatRequest):
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
