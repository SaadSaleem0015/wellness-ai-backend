from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from helpers.jwt_token import get_current_user
from models.user import User
from models.lead import Lead
from models.knowledge_base import Knowledgebase
from models.assistant import Assistant
from models.file import File


dashboard_router = APIRouter()


@dashboard_router.get("/dashboard")
async def get_dashboard(current: Annotated[User, Depends(get_current_user)]):
	try:
		user, company = current

		total_leads = await Lead.filter(file__company=company).count()
		total_knowledge_bases = await Knowledgebase.filter(company=company).count()
		total_assistants = await Assistant.filter(company=company).count()
		total_files = await File.filter(company=company).count()

		return {
			"success": True,
			"totals": {
				"leads": total_leads,
				"knowledge_bases": total_knowledge_bases,
				"assistants": total_assistants,
				"files": total_files,
			}
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")


