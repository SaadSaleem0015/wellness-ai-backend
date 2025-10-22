import os
from typing import Annotated
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    BackgroundTasks,
)
from fastapi.responses import FileResponse
from helpers.jwt_token import get_current_user
from helpers.vapi_helper import delete_from_vapi_file, upload_file_to_vapi
from models.knowledge_base import Knowledgebase
from pathlib import Path
import uuid

from models.user import User


kb_router = APIRouter()


@kb_router.post("/upload")
async def upload_file(
    background: BackgroundTasks,
    current: User = Depends(get_current_user),
    file: UploadFile = File(...),
):
    try:
        user, company = current
        os.makedirs("uploads", exist_ok=True)

        file_content = await file.read()

        files = {"file": (file.filename, file_content, file.content_type)}
        name = file.filename
        vapi_file = await upload_file_to_vapi(files)

        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join("uploads", unique_filename)
        file_format = (
            file.filename.split(".")[-1] if "." in file.filename else "unknown"
        )
        with open(file_path, "wb") as f:
            f.write(file_content)

        metadata = await Knowledgebase.create(
            filename=unique_filename,
            original_filename=file.filename,
            file_format=file_format,
            user=user,
            company = company,
            vapi_id=vapi_file["id"],
        )
        return {
                "success": True,
                "detail": "File is uploaded",
            }
        
        file_size = os.path.getsize(file_path) / 1024
        # if file_size > 1024:
        #     background.add_task(
        #         background_task, file_format, file_path, file, name, user
        #     )
        #     return {
        #         "success": True,
        #         "detail": "File is large so  being processed in the background",
        #     }
        # else:
        #     # Process file immediately
        #     response = await background_task(file_format, file_path, file, name, user)
        #     return response

    
    except Exception as e:
        error_message = str(e).lower()
        print(f"Upload error: {e}")  

        if "api key" in error_message or "authentication" in error_message:
            raise HTTPException(status_code=401, detail="Invalid API key.")
        elif "quota" in error_message or "rate limit" in error_message:
            raise HTTPException(
                status_code=429, detail="OpenAI API quota exceeded. Try again later."
            )
        elif "openai" in error_message or "api error" in error_message:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI API error. Please try again: {error_message}",
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected server error: {str(e)}",
            )



@kb_router.get("/knowledge-base-files")
async def list_files(
    current: Annotated[User, Depends(get_current_user)],
):
    user, company  = current

    files = await Knowledgebase.filter(company=company).all().order_by("id")
    return files


@kb_router.delete("/knowledge-base-files/{documentToDelete}")
async def delete_file(
    documentToDelete: str,
    current: Annotated[User, Depends(get_current_user)],
):
    try:
        user, company  = current

        metadata = await Knowledgebase.get_or_none(vapi_id=documentToDelete, company=company)
        if not metadata:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = os.path.join("uploads", metadata.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        delete_vapi_file = await delete_from_vapi_file(metadata.vapi_id)
        await metadata.delete()

        return {"success": True, "message": "File deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@kb_router.get("/files/{file_id}/download")
async def download_file(
    file_id: int, current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company  = current
        metadata = await Knowledgebase.get_or_none(id=file_id, user=company)
        if not metadata:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = os.path.join("uploads", metadata.filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on server")
        new_file = Path(file_path).resolve()
        return FileResponse(
            path=str(new_file),
            filename=metadata.original_filename,
            headers={"Content-Disposition": "inline"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")




