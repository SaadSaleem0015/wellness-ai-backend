from typing import List
from fastapi import APIRouter, Depends, HTTPException
import requests
from models.tool import Tool
from helpers.vapi_helper import get_headers
from helpers.jwt_token import get_current_user
from models.user import User

tool_router = APIRouter()

@tool_router.get("/tools")
async def get_tools(user: User = Depends(get_current_user)):
    """
    Fetch tools from Vapi API and update the database.
    Tools with the same credentialId will not be saved again.
    If tool type is 'query', use the function.name and function.description instead.
    """
    try:
        headers = get_headers()
        url = "https://api.vapi.ai/tool"
        
        response = requests.get(url, headers=headers)
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Failed to fetch tools from Vapi API: {response.text}"
            )
        
        vapi_tools = response.json()
        updated_tools = []

        for tool_data in vapi_tools:
            vapi_id = tool_data.get("id")
            tool_type = tool_data.get("type", "")
            orgId = tool_data.get("orgId")
            credentialId = tool_data.get("credentialId")

            # If it's a "query" tool, extract from function block
            if tool_type == "query":
                function_data = tool_data.get("function", {})
                name = function_data.get("name", "").replace(" ", "_")  # normalize spaces
                description = function_data.get("description", "")
            else:
                name = tool_data.get("name", "")
                description = tool_data.get("description", "")

            if not vapi_id:
                continue  # skip invalid entries

            existing_tool = None
            if credentialId:
                existing_tool = await Tool.filter(credentialId=credentialId).first()
            
            # Create or update tool record
            if not existing_tool:
                existing_by_vapi_id = await Tool.filter(vapi_id=vapi_id).first()
                
                if not existing_by_vapi_id:
                    new_tool = await Tool.create(
                        name=name,
                        description=description,
                        credentialId=credentialId,
                        orgId=orgId,
                        vapi_id=vapi_id
                    )
                    updated_tools.append(new_tool)
                else:
                    existing_by_vapi_id.name = name
                    existing_by_vapi_id.description = description
                    existing_by_vapi_id.credentialId = credentialId
                    existing_by_vapi_id.orgId = orgId
                    await existing_by_vapi_id.save()
                    updated_tools.append(existing_by_vapi_id)
            else:
                existing_tool.name = name
                existing_tool.description = description
                existing_tool.orgId = orgId
                existing_tool.vapi_id = vapi_id
                await existing_tool.save()
                updated_tools.append(existing_tool)
        
        all_tools = await Tool.all().order_by("id")
        
        return {
            "success": True,
            "message": f"Successfully processed {len(updated_tools)} tools",
            "tools": all_tools
        }
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching tools: {str(e)}"
        )
