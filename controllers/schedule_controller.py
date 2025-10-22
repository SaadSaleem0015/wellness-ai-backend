from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from pydantic import BaseModel
from datetime import datetime
from helpers.jwt_token import get_current_user
from models.user import User
from models.schedule import Schedule
from models.assistant import Assistant
from models.file import File
from models.lead import Lead


schedule_router = APIRouter()


class CreateScheduleRequest(BaseModel):
    assistant_id: int
    file_id: int
    scheduled_at: datetime


@schedule_router.post("/schedule")
async def create_schedule(req: CreateScheduleRequest, current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company = current

        assistant = await Assistant.get_or_none(id=req.assistant_id, company=company)
        if not assistant:
            raise HTTPException(status_code=404, detail="Assistant not found")

        file = await File.get_or_none(id=req.file_id, company=company)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        total_leads = await Lead.filter(file=file).count()

        schedule = await Schedule.create(
            assistant=assistant,
            file=file,
            scheduled_at=req.scheduled_at,
            total_leads=total_leads,
            leads_completed=0,
        )

        return {
            "success": True,
            "id": schedule.id,
            "detail": "Schedule created successfully",
            "total_leads": total_leads,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@schedule_router.get("/schedules")
async def list_schedules(current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company = current
        schedules = await Schedule.filter(assistant__company=company).prefetch_related("assistant", "file")
        return [
            {
                "id": s.id,
                "assistant_id": s.assistant_id,
                "assistant_name": s.assistant.name if s.assistant_id else None,
                "file_id": s.file_id,
                "file_name": s.file.name if s.file_id else None,
                "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
                "is_processed": s.is_processed,
                "total_leads": s.total_leads,
                "leads_completed": s.leads_completed,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in schedules
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schedules: {str(e)}")


@schedule_router.get("/schedule/{schedule_id}")
async def get_schedule(schedule_id: int, current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company = current
        schedule = await Schedule.get_or_none(id=schedule_id, assistant__company=company).prefetch_related("assistant", "file")
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return {
            "id": schedule.id,
            "assistant_id": schedule.assistant_id,
            "assistant_name": schedule.assistant.name if schedule.assistant_id else None,
            "file_id": schedule.file_id,
            "file_name": schedule.file.name if schedule.file_id else None,
            "scheduled_at": schedule.scheduled_at.isoformat() if schedule.scheduled_at else None,
            "is_processed": schedule.is_processed,
            "total_leads": schedule.total_leads,
            "leads_completed": schedule.leads_completed,
            "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schedule: {str(e)}")


@schedule_router.delete("/schedule/{schedule_id}")
async def delete_schedule(schedule_id: int, current: Annotated[User, Depends(get_current_user)]):
    try:
        user, company = current
        schedule = await Schedule.get_or_none(id=schedule_id, assistant__company=company)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        await schedule.delete()
        return {"success": True, "detail": "Schedule deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")


