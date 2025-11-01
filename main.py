from dotenv import load_dotenv

from controllers.knowledge_base_controller import kb_router
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from helpers.tortoise_config import lifespan
from controllers.auth_controller import auth_router
from controllers.booking_controller import booking_router
from controllers.assistant_controller import assistant_router
from controllers.tool_controller import tool_router
from controllers.leads_controller import lead_router
from controllers.twilio_controller import twilio_router
from controllers.dashboard_controller import dashboard_router
from controllers.schedule_controller import schedule_router
from controllers.call_controller import call_log_router
from controllers.content_controller import content_router






app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)


app.include_router(auth_router, prefix='/api', tags=['Authentication'])
app.include_router(booking_router,prefix='/api', tags=['booking'])
app.include_router(assistant_router,prefix='/api', tags=['Assistant'])
app.include_router(tool_router,prefix='/api', tags=['Tools'])
app.include_router(kb_router,prefix='/api', tags=['Knowledge Base'])
app.include_router(lead_router,prefix='/api', tags=['Leads'])
app.include_router(twilio_router,prefix='/api', tags=['Phone Number'])
app.include_router(dashboard_router,prefix='/api', tags=['Dashboard'])
app.include_router(schedule_router,prefix='/api', tags=['Schedule'])
app.include_router(call_log_router,prefix='/api', tags=['Call'])
app.include_router(content_router,prefix='/api', tags=['Call'])










@app.get('/')
def greetings():
    return {
        "Message": "Hello Developers, how are you "
    }