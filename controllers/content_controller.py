import os
import uuid
import requests
from fastapi import APIRouter, FastAPI, Body
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tortoise import Tortoise, fields
from tortoise.models import Model
from openai import OpenAI
from PIL import Image
import io

from models.content import GeneratedContent

content_router = APIRouter()

os.makedirs("static", exist_ok=True)
os.makedirs("static/images", exist_ok=True)

content_router.mount("/static", StaticFiles(directory="static"), name="static")

class GenerateRequest(BaseModel):
    prompt: str

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SD_API_URL = "https://stablediffusionapi.com/api/v3/text2img"
SD_API_KEY = "vYUMxZEDSb4ybW8pjXyNLZis2DeOQOWbTRUx0OWvrNDuLczcJrrgrzvRZHD4"  





@content_router.post("/content/generate")
async def generate_content(request: GenerateRequest = Body(...)):
    input_prompt = request.prompt.strip()
    
    # text_prompt = f"Generate a concise social media post related to medical topics based on: {input_prompt}"
    # response = openai_client.chat.completions.create(
    #     model="gpt-3.5-turbo",
    #     messages=[{"role": "user", "content": text_prompt}],
    #     max_tokens=100,
    #     temperature=0.7
    # )
    # generated_text = response.choices[0].message.content.strip()
    text_prompt = f"Generate a concise social media post related to medical topics based on diet , water etc "
    
    sd_payload = {
        "key": SD_API_KEY,
        "prompt": text_prompt,
        "negative_prompt": "blurry, low quality, deformed",
        "width": 576,
        "height": 1024,
        "samples": 1,
        "num_inference_steps": 20,
        "seed": None,
        "guidance_scale": 7.5,
        "safety_checker": "yes",
        "enhance_prompt": "yes",
        "multi_lingual": "no"
    }
    
    sd_response = requests.post(SD_API_URL, json=sd_payload)
    sd_data = sd_response.json()
    
    if sd_data.get("status") != "success":
        raise ValueError("Image generation failed: " + str(sd_data))
    
    image_url_remote = sd_data["output"][0]
    
    image_response = requests.get(image_url_remote)
    image = Image.open(io.BytesIO(image_response.content))
    
    filename = f"{uuid.uuid4()}.png"
    image_path = f"static/images/{filename}"
    image.save(image_path)
    image_url = f"/static/images/{filename}"
    
    content = await GeneratedContent.create(
        input_prompt=input_prompt,
        generated_text=text_prompt,
        image_url=image_url
    )
    
    return {
        "text": text_prompt,
        "imageUrl": image_url
    }