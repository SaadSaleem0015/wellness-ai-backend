import os
import uuid
import requests
from fastapi import APIRouter, FastAPI, Body, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tortoise import Tortoise, fields
from tortoise.models import Model
from openai import OpenAI
from PIL import Image
import io
from fastapi.responses import FileResponse
import asyncio
# from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, vfx

from models.content import GeneratedContent

content_router = APIRouter()

os.makedirs("static", exist_ok=True)
os.makedirs("static/images", exist_ok=True)

content_router.mount("/static", StaticFiles(directory="static"), name="static")

class GenerateRequest(BaseModel):
    prompt: str
    content_type: str = "image"  # 'image' or 'video'
    # Optional overrides for image/video generation


openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
HEYGEN_KEY = OpenAI(api_key=os.getenv("HEYGEN_API_KEY"))


SD_API_URL = "https://modelslab.com/api/v6/images/text2img"
SD_VIDEO_API_URL = "https://modelslab.com/api/v6/video/text2video"
SD_API_KEY = "vYUMxZEDSb4ybW8pjXyNLZis2DeOQOWbTRUx0OWvrNDuLczcJrrgrzvRZHD4"  



@content_router.post("/content/generate")
async def generate_content(request: GenerateRequest = Body(...)):
    input_prompt = request.prompt.strip()
    
    # ✅ FIXED: Proper caption generation
    caption_prompt = (
        f"Write a **short, engaging social media caption** for a medispa/wellness clinic "
        f"about **treatment: {input_prompt}**. \n"
        f"- **2 key benefits** ✨\n"
        f"- **Gentle CTA**: Book now! DM us! \n"
        f"- **Emojis + 3 hashtags** #Medispa #Beauty\n"
        f"- **<100 chars**."
    )
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",  # ✅ Better
        messages=[{"role": "user", "content": caption_prompt}],
        max_tokens=80,
        temperature=0.8
    )
    generated_caption = response.choices[0].message.content.strip()
    
    # ✅ Visual prompt for IMAGES only
    visual_prompt = (
        f"Luxury medispa: **{input_prompt}** treatment scene. "
        f"Happy diverse client, professional staff, modern spa, "
        f"soft glow lighting, photoreal, 8K, vibrant."
    )
    
    if request.content_type.lower() == "video":
        # 🔥 HEYGEN: Talking avatar reads caption! (~30-90s realistic)
        os.makedirs("static/videos", exist_ok=True)
        
        HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
        if not HEYGEN_API_KEY:
            raise HTTPException(500, "🚨 Set HEYGEN_API_KEY in .env!")
        
        headers = {
            "X-Api-Key": HEYGEN_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Script = Caption!
        script = generated_caption
        
        payload = {
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": "Daisy-inskirt-20220818",  # 👩‍⚕️ Friendly pro
                    "avatar_style": "normal",
                    "scale": 0.9
                },
                "voice": {
                    "type": "text",
                    "voice_id": "2d5b0e6cf36f460aa7fc47e3eee4ba54",  # Warm female
                    "input_text": script,
                    "speed": 1.1  # Faster = shorter video
                },
                "background": {
                    "type": "color",
                    "value": "#f8f4f0"  # Soft spa beige
                }
            }],
            "dimension": {
                "width": 576,   # ✅ 9:16 Reels!
                "height": 1024
            }
        }
        
        # 1. Generate
        resp = requests.post(
            "https://api.heygen.com/v2/video/generate",
            json=payload,
            headers=headers,
            timeout=30
        )
        data = resp.json()
        print("data", data)
        if "error" in data:
            raise ValueError(f"HeyGen: {data['error']}")
        video_id = data["data"]["video_id"]
        
        # 2. **Aggressive Poll** (~10-60s total)
        status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
        for attempt in range(120):  # 6min max
            await asyncio.sleep(3)  # Fast check!
            status_resp = requests.get(status_url, headers={"X-Api-Key": HEYGEN_API_KEY}, timeout=10)
            status_data = status_resp.json()["data"]
            status = status_data["status"]
            
            if status == "completed":
                video_url = status_data["video_url"]
                break
            elif status in ("failed", "error"):
                raise ValueError(f"HeyGen failed: {status_data.get('error', status)}")
        
        else:
            raise ValueError("HeyGen timeout! (Peak hours?)")
        
        # 3. Download
        video_resp = requests.get(video_url, timeout=120, stream=True)
        video_filename = f"{uuid.uuid4()}.mp4"
        video_path = os.path.join("static", "videos", video_filename)
        with open(video_path, "wb") as f:
            for chunk in video_resp.iter_content(8192):
                f.write(chunk)
        local_video_url = f"/static/videos/{video_filename}"
        
        await GeneratedContent.create(
            input_prompt=input_prompt,
            generated_text=generated_caption,  # ✅ Caption!
            content_type="video",
            image_url=None,
            video_url=video_filename,
        )
        
        return {
            "text": generated_caption,  # ✅ FIXED!
            "videoUrl": local_video_url,
            "contentType": "video"
        }
    
    else:  # Image: Keep Flux (fast!)
        sd_payload = {
            "key": SD_API_KEY,
            "model_id": "flux",
            "prompt": visual_prompt,  # ✅ FIXED!
            "negative_prompt": "blurry, low quality, deformed, ugly",
            "width": 576,
            "height": 1024,
            "samples": 1,
            "num_inference_steps": 20,
            "guidance_scale": 7.5,
            "safety_checker": "yes",
            "enhance_prompt": "yes",
            "multi_lingual": "no"
        }
        
        sd_response = requests.post(SD_API_URL, json=sd_payload, timeout=120)
        sd_data = sd_response.json()
        if sd_data.get("status") != "success":
            raise ValueError(f"Image failed: {sd_data}")
        
        image_url_remote = sd_data["output"][0]
        image_response = requests.get(image_url_remote)
        image = Image.open(io.BytesIO(image_response.content))
        
        filename = f"{uuid.uuid4()}.png"
        image_path = f"static/images/{filename}"
        image.save(image_path)
        image_url = f"/static/images/{filename}"
        
        await GeneratedContent.create(
            input_prompt=input_prompt,
            generated_text=generated_caption,
            content_type="image",
            image_url=filename,
            video_url=None,
        )
        
        return {
            "text": generated_caption,  # ✅ FIXED!
            "imageUrl": image_url,
            "contentType": "image"
        }

# @content_router.post("/content/generate")
# async def generate_content(request: GenerateRequest = Body(...)):
#     input_prompt = request.prompt.strip()
    
#     text_prompt = (
#     f"Generate a friendly, professional social-media caption for a medispa or wellness clinic. " 
#     f"The post should highlight a specific medical or beauty treatment, mention a clear benefit, include a gentle call-to-action (e.g., \"book now\", \"learn more\"), " 
#     f"and have the tone of: {input_prompt}"
# )

#     response = openai_client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[{"role": "user", "content": text_prompt}],
#         max_tokens=100,
#         temperature=0.7
#     )
#     generated_text = response.choices[0].message.content.strip()
    
#     if request.content_type.lower() == "video":
#         os.makedirs("static/videos", exist_ok=True)
#         video_payload = {
#             "key": SD_API_KEY,
#             "model_id": "wanx",  
#             "prompt": text_prompt,
#             "negative_prompt": "low quality, blurry, deformed",
#             "height": 512,
#             "width":  512,
#             "num_frames": 25,
#             "num_inference_steps":  20,
#             "guidance_scale": 7,
#             "upscale_height": 640,
#             "upscale_width": 1024,
#             "upscale_strength": 0.6,
#             "upscale_guidance_scale": 12,
#             "upscale_num_inference_steps": 20,
#             "output_type": "mp4"
#         }

#         sd_response = requests.post(SD_VIDEO_API_URL, json=video_payload)
#         sd_data = sd_response.json()

#         # Handle async processing: poll fetch URL until success or timeout
#         if sd_data.get("status") == "processing" and sd_data.get("fetch_result"):
#             fetch_url = sd_data["fetch_result"]
#             max_attempts = 40
#             for _ in range(max_attempts):
#                 await asyncio.sleep(3)
#                 # Provider requires POST for fetch with API key in JSON body
#                 fetch_resp = requests.post(fetch_url, json={"key": SD_API_KEY})
#                 fetch_data = fetch_resp.json()
#                 if fetch_data.get("status") == "success" and fetch_data.get("output"):
#                     sd_data = fetch_data
#                     break
#                 if fetch_data.get("status") not in ("processing", "success"):
#                     raise ValueError("Video generation failed: " + str(fetch_data))
#             else:
#                 raise ValueError("Video generation timed out: " + str(sd_data))

#         if sd_data.get("status") != "success" or not sd_data.get("output"):
#             raise ValueError("Video generation failed: " + str(sd_data))

#         video_url_remote = sd_data["output"][0]

#         video_response = requests.get(video_url_remote)
#         ext = "mp4"
#         video_filename = f"{uuid.uuid4()}.{ext}"
#         video_path = os.path.join("static", "videos", video_filename)
#         with open(video_path, "wb") as f:
#             f.write(video_response.content)
#         local_video_url = f"/static/videos/{video_filename}"

#         await GeneratedContent.create(
#             input_prompt=input_prompt,
#             generated_text=generated_text,
#             content_type="video",
#             image_url=None,
#             video_url=video_filename,
#         )

#         return {
#             "text": text_prompt,
#             "videoUrl": local_video_url,
#             "contentType": "video"
#         }
#     else:
#         sd_payload = {
#             "key": SD_API_KEY,
#             "model_id": "flux",
#             "prompt": text_prompt,
#             "negative_prompt": "blurry, low quality, deformed",
#             "width": 576,
#             "height": 1024,
#             "samples": 1,
#             "num_inference_steps": 20,
#             "seed": None,
#             "guidance_scale": 7.5,
#             "safety_checker": "yes",
#             "enhance_prompt": "yes",
#             "multi_lingual": "no"
#         }
        
#         sd_response = requests.post(SD_API_URL, json=sd_payload)
#         sd_data = sd_response.json()
#         if sd_data.get("status") != "success":
#             raise ValueError("Image generation failed: " + str(sd_data))
        
#         image_url_remote = sd_data["output"][0]
        
#         image_response = requests.get(image_url_remote)
#         image = Image.open(io.BytesIO(image_response.content))
        
#         filename = f"{uuid.uuid4()}.png"
#         image_path = f"static/images/{filename}"
#         image.save(image_path)
#         image_url = f"/static/images/{filename}"
        
#         await GeneratedContent.create(
#             input_prompt=input_prompt,
#             generated_text=generated_text,
#             content_type="image",
#             image_url=filename,
#             video_url=None,
#         )
        
#         return {
#             "text": text_prompt,
#             "imageUrl": image_url,
#             "contentType": "image"
#         }



@content_router.get("/content-image/{filename}")
async def get_image(filename: str):
    base_dir = os.path.abspath(os.path.join("static", "images"))
    
    file_path = os.path.join(base_dir, filename)
    
    file_path = os.path.abspath(file_path)
    if not file_path.startswith(base_dir):
        raise HTTPException(status_code=400, detail="Invalid image path")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path)

@content_router.get("/content/all")
async def list_generated_content():
    # fetch all records
    contents = await GeneratedContent.all().order_by("-created_at")  # assuming there’s a created_at field
    # prepare output
    results = [
        {
            "id": c.id,
            "input_prompt": c.input_prompt,
            "generated_text": c.generated_text,
            "content_type": getattr(c, "content_type", None),
            "image_url": c.image_url,
            "video_url": getattr(c, "video_url", None),
            "created_at": c.created_at.isoformat() if hasattr(c, "created_at") else None
        }
        for c in contents
    ]
    return {"items": results}


@content_router.get("/content-video/{filename}")
async def get_video(filename: str):
    base_dir = os.path.abspath(os.path.join("static", "videos"))
    file_path = os.path.join(base_dir, filename)
    file_path = os.path.abspath(file_path)
    if not file_path.startswith(base_dir):
        raise HTTPException(status_code=400, detail="Invalid video path")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(file_path)




# After saving image
# def image_to_reel(image_path: str, text: str, output_path: str):
#     # Load image (9:16)
#     clip = ImageClip(image_path, duration=5).resize((576,1024))
    
#     # Add text overlay (fade-in)
#     txt = TextClip(text, fontsize=60, color='white', font='Arial-Bold')
#     txt = txt.set_position('center').set_duration(5).crossfadein(1)
    
#     # Composite + ken burns (zoom)
#     video = CompositeVideoClip([clip, txt]).fx(vfx.fadein, 1).fx(vfx.fadeout, 1)
#     video.write_videofile(output_path, fps=24, audio=False)  # Add music?

# image_to_reel(image_path, generated_text, "static/videos/reel.mp4")
# return {"text": text, "videoUrl": "/static/videos/reel.mp4"}  # Update frontend!


# @content_router.post("/post/{platform}")
# async def post_to_platform(platform: str, content_id: int):  # From DB by ID
#     content = await GeneratedContent.get(id=content_id)
#     token_row = await SocialTokens.filter(user_id=1, platform=platform).first()  # Your user
    
#     if not token_row:
#         raise HTTPException(400, "Connect account first!")
    
#     image_url = f"http://your-domain.com{content.image_url}"  # Public!
    
#     if platform == "facebook":
#         resp = requests.post(
#             f"https://graph.facebook.com/v20.0/{token_row.page_id}/photos",
#             params={"access_token": token_row.access_token, "url": image_url, "message": content.generated_text}
#         )
    
#     elif platform == "instagram":
#         # Step 1: Container
#         container = requests.post(
#             f"https://graph.facebook.com/v20.0/{token_row.page_id}/media",  # IG_USER_ID
#             params={"access_token": token_row.access_token},
#             json={"image_url": image_url, "caption": content.generated_text, "alt_text": "Wellness tip"}
#         ).json()["id"]
        
#         # Step 2: Publish (poll status if needed)
#         resp = requests.post(
#             f"https://graph.facebook.com/v20.0/{token_row.page_id}/media_publish",
#             params={"access_token": token_row.access_token},
#             json={"creation_id": container}
#         )
    
#     elif platform == "tiktok":
#         # Photo Post (PULL_FROM_URL)
#         resp = requests.post(
#             "https://open.tiktokapis.com/v2/post/publish/content/init/",
#             headers={"Authorization": f"Bearer {token_row.access_token}"},
#             json={
#                 "post_info": {"title": content.generated_text[:100], "privacy_level": "PUBLIC_TO_EVERYONE"},
#                 "source_info": {"source": "PULL_FROM_URL", "photo_images": [image_url]},
#                 "post_mode": "DIRECT_POST", "media_type": "PHOTO"
#             }
#         )
    
#     if resp.status_code != 200:
#         raise HTTPException(500, resp.text)
    
#     return {"success": True, "post_id": resp.json().get("id")}