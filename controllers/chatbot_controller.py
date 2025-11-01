from fastapi import APIRouter
from pydantic import BaseModel
from helpers.chat_chain import chat_with_agent
from models.chat import Chat
from models.chat_message import  ChatMessage



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


