from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from helpers.tortoise_config import lifespan
from controllers.auth_controller import auth_router





app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)


app.include_router(auth_router, prefix='/api', tags=['Authentication'])

@app.get('/')
def greetings():
    return {
        "Message": "Hello Developers, how are you "
    }