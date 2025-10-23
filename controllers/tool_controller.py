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
    Fetch tools from Vapi API and sync with the database:
    - Create or update tools that exist in Vapi.
    - Delete tools from DB that no longer exist in Vapi.
    """
    try:
        headers = get_headers()
        url = "https://api.vapi.ai/tool"

        # Step 1: Fetch from Vapi
        response = requests.get(url, headers=headers)
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch tools from Vapi API: {response.text}",
            )

        vapi_tools = response.json()
        updated_tools = []

        # Step 2: Extract all vapi_ids coming from API
        vapi_tool_ids = {tool.get("id") for tool in vapi_tools if tool.get("id")}

        # Step 3: Get all current tools from DB
        existing_tools = await Tool.all()
        existing_tool_ids = {tool.vapi_id for tool in existing_tools if tool.vapi_id}

        # Step 4: Delete any tool that’s not present in Vapi anymore
        deleted_tool_ids = existing_tool_ids - vapi_tool_ids
        if deleted_tool_ids:
            await Tool.filter(vapi_id__in=list(deleted_tool_ids)).delete()

        # Step 5: Create/Update tools from Vapi
        for tool_data in vapi_tools:
            vapi_id = tool_data.get("id")
            tool_type = tool_data.get("type", "")
            orgId = tool_data.get("orgId")
            credentialId = tool_data.get("credentialId")

            # Handle query-type tools
            if tool_type == "query":
                function_data = tool_data.get("function", {})
                name = function_data.get("name", "").replace(" ", "_")
                description = function_data.get("description", "")
            else:
                name = tool_data.get("name", "")
                description = tool_data.get("description", "")

            if not vapi_id:
                continue

            existing_tool = None
            if credentialId:
                existing_tool = await Tool.filter(credentialId=credentialId).first()

            if not existing_tool:
                existing_by_vapi_id = await Tool.filter(vapi_id=vapi_id).first()
                if not existing_by_vapi_id:
                    new_tool = await Tool.create(
                        name=name,
                        description=description,
                        credentialId=credentialId,
                        orgId=orgId,
                        vapi_id=vapi_id,
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
            "message": f"Synced {len(updated_tools)} tools. Deleted {len(deleted_tool_ids)} old tools.",
            "tools": all_tools,
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while syncing tools: {str(e)}",
        )
