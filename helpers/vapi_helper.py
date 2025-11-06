import os
from dotenv import load_dotenv
import httpx

import requests
from models.user import User


load_dotenv()



vapi_api_key = os.environ["VAPI_API_KEY"]
vapi_org_id = os.environ["VAPI_ORG_ID"]

def generate_token():
    return vapi_api_key




async def user_add_payload(assistant_data,user):
    user = await User.filter(id=user.id).first()
    tools = assistant_data.tools

   

    
    if assistant_data.voice_provider == "deepgram":
        voice_model = "aura"
    else:
        voice_model = "eleven_flash_v2_5"
        
        

    user_payload = {
        "transcriber": {
            "provider": assistant_data.transcribe_provider,
            "model": assistant_data.transcribe_model,
            "language": assistant_data.transcribe_language,
        },
        "model": {
            "messages": [
                {
                    "content": assistant_data.systemPrompt,
                    "role": "system"
                }
            ],
            "provider": assistant_data.provider,
            "model": assistant_data.model,
            "temperature": assistant_data.temperature,
            "toolIds": assistant_data.tools if tools else [],
            "maxTokens": assistant_data.maxTokens,
        },
        "voice": {
            "provider": assistant_data.voice_provider,
            "voiceId": assistant_data.voice,
            "model":voice_model,
        },
        "name": assistant_data.name,
        "firstMessage": assistant_data.first_message,
        "endCallPhrases": assistant_data.endCallPhrases,
        # "analysisPlan": {
        #     "summaryPrompt": assistant_data.systemPrompt,
        # },
        "voicemailDetection": {
        "provider": "twilio",
        "voicemailDetectionTypes": ["machine_end_beep", "machine_end_silence"],
        "enabled": True,
        "machineDetectionTimeout": 3,
        "machineDetectionSpeechThreshold": 1000,
        "machineDetectionSpeechEndThreshold": 500,
        "machineDetectionSilenceTimeout": 2000
        }
    }

    end_call_tool = {
        "type": "endCall",
        "messages": [
            {
                "type": "request-complete",
                "content": "Voicemail detected. Ending call immediately."
            }
        ]
    }

    if assistant_data.forwardingPhoneNumber:
        user_payload["forwardingPhoneNumber"] = assistant_data.forwardingPhoneNumber
        
        user_payload["model"]["tools"] = [
            {
                "type": "transferCall",
                "destinations": [
                    {
                        "type": "number",
                        "number": assistant_data.forwardingPhoneNumber,
                        "description": "Transfer to customer support",
                    }
                ]
            },
            end_call_tool
        ]
    else:
        user_payload["model"]["tools"] = [end_call_tool]

    # if assistant_data.knowledgeBase and len(assistant_data.knowledgeBase) > 0:
    #     tool_response = await create_query_tool(assistant_data.knowledgeBase)
        
    #     if tool_response is None:
    #         print("Error: Tool creation failed.")
    #     else:
    #         tool_id = tool_response.get("id") 
            
    #         if not tool_id:
    #             user_payload["model"]["toolIds"] = []
    #         else:
    #             user_payload["model"]["toolIds"] = [tool_id]
    #             print(f"Tool ID: {tool_id}")
    # else:
    #     print("No knowledgeBase provided or it's empty. Skipping tool creation.")
    #     user_payload["model"]["toolIds"] = []
    
    print(user_payload)
    return user_payload


# async def create_query_tool(file_ids, tool_name="Query-Tool"):
#     url = "https://api.vapi.ai/tool/"
#     headers = {
#         "Authorization": f"Bearer {vapi_api_key}",
#         "Content-Type": "application/json"
#     }
#     data = {
#         "type": "query",
#         "function": {"name": tool_name},
#         "knowledgeBases": [
#             {
#                 "provider": "google",
#                 "name": "product_kb",
#                 "description": "Use this knowledge base when the user asks or queries about the product or services",
#                 "fileIds": file_ids
#             }
#         ]
#     }

#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(url, headers=headers, json=data)
#             if response.status_code in [200, 201]:
#                 return response.json() 
#             else:
#                 return None

#     except httpx.RequestError as e:
#         print(f"An error occurred while requesting the tool creation: {e}")
#         return None
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#         return None


async def create_query_tool(file_ids, tool_name="Query-Tool"):
    url = "https://api.vapi.ai/tool/"
    headers = {
        "Authorization": f"Bearer {vapi_api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "type": "query",
        "function": {"name": tool_name},
        "knowledgeBases": [
            {
                "provider": "google",
                "model": "gemini-2.0-flash-lite",
                "name": "product_kb",
                "description": "Use this knowledge base when the user asks or queries about the product or services",
                "fileIds": file_ids
            }
        ]
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            print("response", response.json())

            if response.status_code in [200, 201]:
                print("response", response.json())
                return response.json() 
            else:
                return None

    except httpx.RequestError as e:
        print(f"An error occurred while requesting the tool creation: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


async def create_knowledgebase_tool(file_id, filename):
    """Create a query tool for a specific knowledge base file with naming convention: knowledgebase + filename"""
    # Clean filename for tool name (remove extension and special characters)
    import re
    clean_filename = filename.split('.')[0]
    # Remove all characters that don't match the regex pattern [a-zA-Z0-9_-]
    clean_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', clean_filename)
    # Ensure it doesn't start with a number or underscore
    if clean_filename and (clean_filename[0].isdigit() or clean_filename[0] == '_'):
        clean_filename = 'kb_' + clean_filename
    # Ensure it's not empty and limit to 64 characters
    if not clean_filename:
        clean_filename = 'kb_file'
    tool_name = f"knowledgebase_{clean_filename}"[:64]
    
    url = "https://api.vapi.ai/tool/"
    headers = {
        "Authorization": f"Bearer {vapi_api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "type": "query",
        "function": {"name": tool_name},
        "knowledgeBases": [
            {
                "provider": "google",
                "model": "gemini-2.0-flash-lite",
                "name": f"kb_{clean_filename}"[:64],
                "description": f"Knowledge base for {filename}",
                "fileIds": [file_id]
            }
        ]
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            print("Knowledge base tool response:", response.json())

            if response.status_code in [200, 201]:
                return response.json() 
            else:
                return None

    except httpx.RequestError as e:
        print(f"An error occurred while creating knowledge base tool: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while creating knowledge base tool: {e}")
        return None


data = {
    "user@example.com": {
        "username": "user@example.com",
        "full_name": "User Example",
        "email": "user@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False,
    }
}


def get_headers():
    token = generate_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    return headers

def get_file_headers():
    token = generate_token()
    headers = {
        "Authorization": f"Bearer {token}",
    }
    return headers


async def assistant_payload(assistant_data,company_id):
    
    # assigned_languages = await AssignedLanguage.filter(company_id=company_id).first()

    # if assigned_languages and assigned_languages.language:
    
    #     if isinstance(assigned_languages.language, list):
    #         languages = ", ".join(assigned_languages.language)
    #     else:
    #         languages = assigned_languages.language
        
    #     systemprompt = f"{assistant_data.systemPrompt} Please note, you can only communicate in the : **{languages}** languages. Any other language will not be understood, and responses will be given only in these languages. If you detect a voicemail or answering machine, immediately end the call using the endCall function."
    # else:
    #     systemprompt = f"{assistant_data.systemPrompt} Please note, you can only communicate in **English**. Any other language will not be understood, and responses will be in English only. If you detect a voicemail or answering machine, immediately end the call using the endCall function."

    
    if assistant_data.voice_provider == "deepgram":
        voice_model = "aura"
    else:
        voice_model = "eleven_flash_v2_5"
        
        
    # Ensure fileIds are strings
    kb_file_ids2 = []
    if getattr(assistant_data, 'knowledgeBase', None):
        try:
            kb_file_ids2 = [str(fid) for fid in assistant_data.knowledgeBase]
        except Exception:
            kb_file_ids2 = []

    user_payload = {
        "transcriber": {
            "provider": assistant_data.transcribe_provider,
            "model": assistant_data.transcribe_model,
            "language": assistant_data.transcribe_language,
        },
        "model": {
            "messages": [
                {
                    "content": assistant_data["systemPrompt"],
                    "role": "system"
                }
            ],
            "provider": assistant_data.provider,
            "model": assistant_data.model,
            "temperature": assistant_data.temperature,
            "knowledgeBase": {
                "provider": "canonical",
                "topK": 5,
                "fileIds": kb_file_ids2
            },
            "maxTokens": assistant_data.maxTokens,
        },
        "voice": {
            "provider": assistant_data.voice_provider,
            "voiceId": assistant_data.voice,
            "model":voice_model,
        },
        "name": assistant_data.name,
        #   "hooks": [
        #   {
        #     "on": "customer.speech.timeout",
        #     "options": { "timeoutSeconds": 5 },
        #     "do": [{ "type": "say", "exact": "Are you still there?" }]
        #     }
        # ],
        "firstMessage": assistant_data.first_message,
        "endCallPhrases": assistant_data.endCallPhrases,
        "analysisPlan": {
            "summaryPrompt": assistant_data.systemPrompt,
        },
        "voicemailDetection": {
        "provider": "twilio",
        "voicemailDetectionTypes": ["machine_end_beep", "machine_end_silence"],
        "enabled": True,
        }
            }

    end_call_tool = {
        "type": "endCall",
        "messages": [
            {
                "type": "request-complete",
                "content": "Voicemail detected. Ending call immediately."
            }
        ]
    }

    if assistant_data.forwardingPhoneNumber:
        user_payload["forwardingPhoneNumber"] = assistant_data.forwardingPhoneNumber
        
        user_payload["model"]["tools"] = [
            {
                "type": "transferCall",
                "destinations": [
                    {
                        "type": "number",
                        "number": assistant_data.forwardingPhoneNumber,
                        "description": "Transfer to customer support",
                    }
                ]
            },
            end_call_tool
        ]
    else:
        user_payload["model"]["tools"] = [end_call_tool]

    if assistant_data.knowledgeBase and len(assistant_data.knowledgeBase) > 0:
        tool_response = await create_query_tool(assistant_data.knowledgeBase)
        
        if tool_response is None:
            print("Error: Tool creation failed.")
        else:
            tool_id = tool_response.get("id") 
            
            if not tool_id:
                user_payload["model"]["toolIds"] = []
            else:
                user_payload["model"]["toolIds"] = [tool_id]
                print(f"Tool ID: {tool_id}")
    else:
        print("No knowledgeBase provided or it's empty. Skipping tool creation.")
        user_payload["model"]["toolIds"] = []
    
    print(user_payload)
    return user_payload


async def create_vapi_tool(files):
    url = "https://api.vapi.ai/tool/"
    headers = {
        "Authorization": f"Bearer {vapi_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "type": "query",
        "function": {"name": "knowledge-base-query"},
        "knowledgeBases": [
            {
                "provider": "google",
                "name": "product_kb",
                "description": "Use this knowledge base when the user asks or queries about the product or services",
                "fileIds": files,
            }
        ],
    }
    try:

        response = requests.post(url, json=data, headers=headers)
        return response.json()
    except Exception as e:
        return e

async def upload_file_to_vapi(file):
    url = f"https://api.vapi.ai/file"
    headers = {
        "Authorization": f"Bearer {vapi_api_key}",
        # "Content-Type": "application/json"
    }
    data = {"file": file}
    try:

        response = requests.post(url, files=file, headers=headers)
        return response.json()
    except Exception as e:
        return e


async def delete_from_vapi_file(id):
    url = f"https://api.vapi.ai/file/{id}"
    headers = {
        "Authorization": f"Bearer {vapi_api_key}",
        "Content-Type": "application/json",
    }
    try:

        response = requests.delete(url, headers=headers)
        return response.json()
    except Exception as e:
        return e


async def delete_vapi_tool(tool_id):
    """Delete a VAPI tool by its ID"""
    url = f"https://api.vapi.ai/tool/{tool_id}"
    headers = {
        "Authorization": f"Bearer {vapi_api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.delete(url, headers=headers)
        return response.json()
    except Exception as e:
        return e


async def get_all_call_list(date):
    if date:
       call_list_url = f"https://api.vapi.ai/call?createdAtGt={date}"
    else:
      call_list_url = f"https://api.vapi.ai/call"
    headers = {
        "Authorization": f"Bearer {os.environ.get('VAPI_API_KEY')}",
    }
    call_list = requests.get(call_list_url, headers=headers)
    call_list_json = call_list.json()

    return call_list_json