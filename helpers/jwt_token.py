import jwt
import os
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
from typing import Annotated
from models.user import User

security = HTTPBearer()

def generate_user_token(payload: dict):
    jwt_key = os.getenv("JWT_SECRET")
    if not jwt_key:
        raise ValueError("JWT_SECRET environment variable is not set")
    token = jwt.encode(payload, jwt_key, algorithm='HS256')
    return token

def decode_user_token(token: str):
    try:
        jwt_key = os.getenv("JWT_SECRET")
        if not jwt_key:
            raise ValueError("JWT_SECRET environment variable is not set")
        return jwt.decode(token, jwt_key, algorithms=['HS256'])
    except:
        raise HTTPException(status_code=401, detail="Invalid Token")


async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    try:
        token = credentials.credentials

        user_credential = decode_user_token(token=token)
    except:
        raise HTTPException(status_code=401, detail="Invalid Token")
        

    if user_credential:
        user = await User.filter(id=user_credential["id"]).prefetch_related("company").first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid Credentials")

        company = await user.company if user.company_id else None
        return user, company

    raise HTTPException(status_code=401, detail="Invalid Token")
