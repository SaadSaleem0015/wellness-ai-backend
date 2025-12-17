import os
import uuid
import requests
from fastapi import APIRouter, Depends, Body, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
from PIL import Image
import io
from fastapi.responses import FileResponse
import asyncio
# from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, vfx

from helpers.jwt_token import get_current_user
from models.content import GeneratedContent
from models.uploadedasset import UploadedAsset
from models.user import User
VOICES = [
    "653f266cdf734030b168a55440109f6d",  # drtumbaga.rnva
    "8541859128fe4a0a9f0eddeebf0039b9",  # Dr.Tumbaga
    "2c2b9403b94040189ce9a0db5ca8a553",  # MyRec_0731_1142excited.m4a
    "6b98b17f036547f98f15d4c69feae1c9",  # MyRec_0731_1141 calm.m4a
    "86eb19cf71a546d686630002b53c5c4a",  # MyRec_0731_1142excited (1).m4a
    "87edb521f4e94956ac1552a15c127f68",  # Dr.Tumbaga (Eye Contact Correction)
    "7c556490cb3e49b6990f689cb5048edc",  # Dr.Tumbaga
    "7de169ed7f90458ca7f600be7b913612",  # MyRec_0731_1142excited.m4a
]
content_router = APIRouter()

os.makedirs("static", exist_ok=True)
os.makedirs("static/images", exist_ok=True)

content_router.mount("/static", StaticFiles(directory="static"), name="static")

class GenerateRequest(BaseModel):
    prompt: str
    content_type: str = "image"  # 'image' or 'video'
    # Optional overrides for image/video generation
class CustomGenerateRequest(BaseModel):
    prompt: str  # Treatment prompt, e.g., "Botox injection"
    voice_id: str  # Selected from VOICES
    custom_motion_prompt: str | None = None  # Optional motion, e.g., "gentle hand gestures"
    video_title: str = "Medispa Treatment Video"  # Default; customizable
    assetId : int 

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
HEYGEN_KEY = OpenAI(api_key=os.getenv("HEYGEN_API_KEY"))


SD_API_URL = "https://modelslab.com/api/v6/images/text2img"
SD_VIDEO_API_URL = "https://modelslab.com/api/v6/video/text2video"
SD_API_KEY = "vYUMxZEDSb4ybW8pjXyNLZis2DeOQOWbTRUx0OWvrNDuLczcJrrgrzvRZHD4"  


@content_router.get("/avatars")
async def get_avatars():
    HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")

    if not HEYGEN_API_KEY:
        raise HTTPException(status_code=500, detail="🚨 Missing HEYGEN_API_KEY in environment variables")

    url = "https://api.heygen.com/v2/avatars"
    headers = {
        "accept": "application/json",
        "X-Api-Key": HEYGEN_API_KEY
    }

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HeyGen request failed: {str(e)}")

    # 🎯 Normalize output if needed
    if "data" not in data:
        raise HTTPException(status_code=500, detail=data)

    avatars = data["data"].get("avatars", [])

    # ✅ Return simple structured data
    formatted_list = [
        {
            "id": a.get("avatar_id"),
            "name": a.get("avatar_name"),
            "category": a.get("category"),
            "preview": a.get("preview"),
        }
        for a in avatars
    ]

    return {"items": formatted_list}



@content_router.post("/content/generate")
async def generate_contents(request: GenerateRequest = Body(...)):
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
    
    visual_prompt = (
        f"Luxury medispa: **{input_prompt}** treatment scene. "
        f"Happy diverse client, professional staff, modern spa, "
        f"soft glow lighting, photoreal, 8K, vibrant."
    )
    
    if request.content_type.lower() == "video":
        os.makedirs("static/videos", exist_ok=True)
        
        HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
        if not HEYGEN_API_KEY:
            raise HTTPException(500, "HEYGEN_API_KEY not set!")

        headers = {
            "X-Api-Key": HEYGEN_API_KEY,
            "Content-Type": "application/json"
        }
        
        script = generated_caption

        trimmed_script = script.split("#")[0].strip()

        payload = {
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": "f4afa6d452b64c3990b575dfc8a39d04",
                    "avatar_style": "normal",
                    "scale": 3.2
                },
                "voice": {
                    "type": "text",
                    "voice_id": "86eb19cf71a546d686630002b53c5c4a",
                    "input_text": trimmed_script,
                    "speed": 0.9
                },
                "background": {
                    "type": "color",
                    "value": "#f8f4f0"
                }
            }],
            "dimension": {
            "width": 720,      # Free tier fully supports 720p
            "height": 1280     # Perfect 9:16 ratio
        },
            "orientation": "portrait"
        
        }

        # 1. Generate video
        resp = requests.post(
            "https://api.heygen.com/v2/video/generate",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        resp.raise_for_status()  # Catches 4xx/5xx
        data = resp.json()
        print("data--------------------", data)
        if not data.get("code") != 0 or data.get("data") is None:
            raise ValueError(f"HeyGen API Error: {data.get('message', data)}")

        video_id = data["data"]["video_id"]
        print(f"HeyGen video_id: {video_id}")

        # 2. Poll status
        status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
        video_url = None

        for attempt in range(60):  # ~3 minutes max
            await asyncio.sleep(3)
            status_resp = requests.get(status_url, headers={"X-Api-Key": HEYGEN_API_KEY})
            status_resp.raise_for_status()
            status_data = status_resp.json()

            status = status_data["data"]["status"]
            print(f"Polling... status: {status}")

            if status == "completed":
                video_url = status_data["data"]["video_url"]
                break
            elif status in ("failed", "error"):
                raise ValueError(f"HeyGen processing failed: {status_data['data'].get('error_message', status)}")

        if not video_url:
            raise TimeoutError("HeyGen video generation timed out")

        # 3. Download
        video_resp = requests.get(video_url, stream=True, timeout=120)
        video_resp.raise_for_status()

        video_filename = f"{uuid.uuid4()}.mp4"
        video_path = os.path.join("static", "videos", video_filename)

        with open(video_path, "wb") as f:
            for chunk in video_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        local_video_url = f"/static/videos/{video_filename}"

        # Save to DB
        await GeneratedContent.create(
            input_prompt=input_prompt,
            generated_text=generated_caption,
            content_type="video",
            image_url=None,
            video_url=video_filename,
        )
       
        print("ithy tk ty a gya")
        return {
            "success"  :True, 
            "text": generated_caption,
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
            heygen_video_id = video_id
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



@content_router.post("/upload-photo")
async def upload_photo_for_avatar(
    file: UploadFile = File(..., description="Photo of Dr. T or product (PNG/JPEG)"),     current: User = Depends(get_current_user),

):

    """
    Upload a single photo to HeyGen, store asset with image_key in DB.
    Use for Dr. T recreated poses from Gemini.
    Returns asset details including image_key for video generation.
    """
    user, company = current
    content_type = file.content_type
    if not content_type or not content_type.startswith("image/"):
        raise HTTPException(400, f"Invalid file type: {content_type}. Use PNG/JPEG.")

    content = await file.read()  # In-memory read

    headers = {
        "X-API-KEY": HEYGEN_KEY,
        "accept": "application/json",
        "Content-Type": content_type
    }

    response = requests.post(
        "https://upload.heygen.com/v1/asset",
        headers=headers,
        data=content
    )

    if response.status_code != 200:
        raise HTTPException(400, f"Upload failed: {response.text}")

    data = response.json()
    if data.get("code") != 100:
        raise HTTPException(400, data.get("message", "HeyGen upload error"))

    asset_data = data["data"]
    if asset_data["file_type"] != "image":
        raise HTTPException(400, "Only image assets supported for avatars")


    # Persist to DB
    db_asset = await UploadedAsset.create(
        company=company,
        user = user,
        name=file.filename,
        heygen_id=asset_data["id"],
        image_key=asset_data["image_key"],
        file_type=asset_data["file_type"],
        url=asset_data["url"]
    )

    return db_asset

@content_router.post("/content/generate")
async def generate_contents(request: CustomGenerateRequest = Body(...), current: User = Depends(get_current_user)):
    """
    Generates a video-only content for medispa treatment using HeyGen Avatar IV.
    Workflow: Generate caption → Use uploaded image_key → Create async video → Poll & download → Store locally.
    Frontend: First upload photo via /upload-photo, get asset_id/image_key, then call this with asset_id.
    """
    user, company = current
    input_prompt = request.prompt.strip()

    # Generate engaging caption with GPT
    caption_prompt = (
        f"Write a **short, engaging social media caption** for a medispa/wellness clinic "
        f"about **treatment: {input_prompt}**. \n"
        f"- **2 key benefits** ✨\n"
        f"- **Gentle CTA**: Book now! DM us! \n"
        f"- **Emojis + 3 hashtags** #Medispa #Beauty\n"
        f"- **<100 chars**."
    )

    response = openai_client.chat.completions.create(  # Assuming openai_client is defined elsewhere
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": caption_prompt}],
        max_tokens=80,
        temperature=0.8
    )
    generated_caption = response.choices[0].message.content.strip()

    # Validate voice
    if request.voice_id not in VOICES:
        raise HTTPException(400, "Invalid voice_id; must match available voices")

    # Get asset (frontend must provide asset_id from upload; extend request if needed)
    # For simplicity, assuming request includes asset_id; add to GenerateRequest if not
    # asset = await UploadedAsset.get_or_none(id=request.asset_id, client_id=client_id)  # Uncomment & adjust
    # For demo, hardcode or fetch latest; in prod, require asset_id in request
    asset = await UploadedAsset.filter(company=company, id = request.assetId).order_by('-id').first()  # Latest asset for this client
    if not asset or not asset.image_key:
        raise HTTPException(400, "No valid uploaded asset found. Upload photo first via /upload-photo.")

    # Prepare HeyGen payload for Avatar IV
    payload = {
        "image_key": asset.image_key,
        "title": request.video_title,
        "script": generated_caption,  # Full caption as script (trim hashtags if too long; <5000 chars ok)
        "voice_id": request.voice_id,
        "video_orientation": "portrait",
        "avatar_fit": "contain"  # Or "cover"; adjust as needed
    }

    if request.custom_motion_prompt:
        payload["custom_motion_prompt"] = request.custom_motion_prompt
        payload["enhance_motion"] = True  # AI enhances for better results

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": HEYGEN_KEY
    }

    # 1. Generate video (async)
    resp = requests.post(
        "https://api.heygen.com/v2/video/av4/generate",
        json=payload,
        headers=headers,
        timeout=30
    )

    resp.raise_for_status()
    data = resp.json()
    print("HeyGen response:", data)  # For debugging
    if data.get("code") != 100 or not data.get("data"):
        raise HTTPException(400, f"HeyGen API Error: {data.get('message', str(data))}")

    heygen_video_id = data["data"]["video_id"]  # Assumed field; confirm via docs/logs
    print(f"HeyGen video_id: {heygen_video_id}")

    # 2. Poll status (updated endpoint per docs)
    status_url = f"https://api.heygen.com/v1/video_status.get?video_id={heygen_video_id}"
    video_url = None

    for attempt in range(60):  # ~3 min max; adjust for longer scripts
        await asyncio.sleep(3)
        status_resp = requests.get(
            status_url,
            headers={"x-api-key": HEYGEN_KEY},
            timeout=10
        )
        status_resp.raise_for_status()
        status_data = status_resp.json()

        status = status_data["data"]["status"]  # Assumed path
        print(f"Polling... status: {status}")

        if status == "completed":
            video_url = status_data["data"]["video_url"]
            break
        elif status in ("failed", "error"):
            raise HTTPException(400, f"HeyGen processing failed: {status_data['data'].get('error_message', status)}")

    if not video_url:
        raise HTTPException(500, "HeyGen video generation timed out")

    # 3. Download & save locally
    os.makedirs("static/videos", exist_ok=True)
    video_resp = requests.get(video_url, stream=True, timeout=120)
    video_resp.raise_for_status()

    video_filename = f"{uuid.uuid4()}.mp4"
    video_path = os.path.join("static", "videos", video_filename)

    with open(video_path, "wb") as f:
        for chunk in video_resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    local_video_url = f"/static/videos/{video_filename}"

    # 4. Save to DB (adapt to your GeneratedContent if different; here using GeneratedVideo for alignment)
    db_video = await GeneratedContent.create(
        company=company,
        user = user,
        asset=asset,
        video_title = request.video_title,
        input_prompt = input_prompt,
        generated_text=generated_caption,
        voice_id=request.voice_id,
        motion_prompt=request.custom_motion_prompt,
        heygen_video_id=heygen_video_id,
        video_url=video_filename  # Local filename
    )

    print("Video generated and saved successfully")

    return {
        "success": True,
        "text": generated_caption,
        "videoUrl": local_video_url,
        "contentType": "video",
        "video_id": db_video.id  # For optional status repoll if needed
    }

# Optional: Status endpoint (if frontend wants to poll independently)
# @content_router.get("/video/{video_id}/status", response_model=GeneratedVideo_Pydantic)
# async def get_video_status(video_id: int):
#     """
#     Poll for video status (if not handled in generate). Updates DB on completion.
#     """
#     db_video = await GeneratedVideo.get_or_none(id=video_id)
#     if not db_video:
#         raise HTTPNotFoundError("Video not found")

#     if db_video.status == "completed":
#         return db_video

#     # Poll HeyGen
#     status_url = f"https://api.heygen.com/v1/video_status.get?video_id={db_video.heygen_video_id}"
#     status_resp = requests.get(
#         status_url,
#         headers={"x-api-key": HEYGEN_API_KEY},
#         timeout=10
#     )
#     status_resp.raise_for_status()
#     status_data = status_resp.json()

#     heygen_status = status_data["data"]["status"]
#     db_video.status = heygen_status

#     if heygen_status == "completed":
#         # If not downloaded yet, download here (but in main flow, it's done)
#         db_video.video_url = status_data["data"]["video_url"]  # Remote; download if needed

#     await db_video.save()
#     return await GeneratedVideo_Pydantic.from_tortoise_orm(db_video)