from fastapi import APIRouter,Depends,Request,Form,BackgroundTasks,Response,HTTPException
from twilio.twiml.messaging_response import MessagingResponse
from pydantic import BaseModel,HttpUrl
import os
from helpers.scrapper.web_crawller import crawl_and_save_urls,refine_urls
from helpers.scrapper.web_scrapper import quick_scrape
from helpers.scrapper.test import beautifulsoap_scrape
from helpers.scrapper.test import scrape_and_refine




webscrapperrouter = APIRouter()

class ChatRequest(BaseModel):
    url: HttpUrl

class ChatSettingRequest(BaseModel):
    prompt: str
    model: str
    openai_key: str




@webscrapperrouter.post("/get-urls")
async def chatbot_endpoint(request:ChatRequest,background_tasks:BackgroundTasks):

    try:
        
        background_tasks.add_task(scraping_task,str(request.url))
        return{
            "success":True,
            "data":"scrapping the website"
        }
    except Exception as error:
        raise HTTPException(status_code=500,detail=f"error {error} occured")


async def scraping_task(url:str):
    try:
       
        crawller  = await crawl_and_save_urls(url)
       
        refined_urls = await refine_urls(crawller.get("urls"))
        print(f"refined urls are these {refined_urls}")
        for url in refined_urls:
            await scrape_and_refine(url)
        
        
        
    except Exception as error:
        print(f"error in scrapper task is this {error}")
        raise HTTPException(status_code=500,detail=f"error is this {error}")


