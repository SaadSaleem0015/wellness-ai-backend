from fastapi import APIRouter, HTTPException, Depends
from argon2 import PasswordHasher
from pydantic import BaseModel, EmailStr
from typing import Annotated,Optional
from models.user import User, UserType
from models.company import Company
from models.code import Code
from helpers.jwt_token import generate_user_token, get_current_user
import os
from enum import Enum

from typing import Literal



auth_router = APIRouter()
ph = PasswordHasher()


class SignupPayload(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginPayload(BaseModel):
    email: str
    password: str

class AccountVerificationPayload(BaseModel):
    email: EmailStr
    code: int

class PasswordResetCode(BaseModel):
    email: EmailStr

class VerifyCodePayload(BaseModel):
    email: EmailStr
    code: str
    
class ResetCodePayload(BaseModel):
    email: EmailStr
    code: str
    password: str
    
class UpdateProfilePayload(BaseModel):
    email: EmailStr
    name: str
    newPassword: Optional[str] = None
    password:Optional[str] = None
    
    



class AccessChangePayload(BaseModel):
    name:str
    password:str

@auth_router.post('/signup')
async def  signup(payload: SignupPayload):
    user = await User.filter(email = payload.email).first()
    if user: 
        raise HTTPException(status_code=400, detail="User already exists")
    try:
        user = User(
            name = payload.name,
            email = payload.email,
            password = ph.hash(payload.password),
        )
        await user.save()

        # Create a company for this new user and assign as main admin
        try:
            first_name = payload.name.split()[0] if payload.name else ""
            # e.g., "Saad's company"
            company_name = f"{first_name}'s company" if first_name else "My company"
            company = await Company.create(
                company_name=company_name,
                admin_name=payload.name
            )
            user.company = company
            user.main_admin = True
            await user.save()
        except Exception as ce:
            # If company creation fails, clean up the created user to avoid orphaned records
            try:
                await user.delete()
            except:
                pass
            raise HTTPException(status_code=400, detail=f"Failed to create company: {ce}")
     
        return {
                "success": True, 
                "verify": True,
                "detail": "User and company created successfully" ,
                "data": {
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "main_admin": user.main_admin
                    },
                    "company": {
                        "id": user.company_id,
                        "company_name": company.company_name,
                        "admin_name": company.admin_name
                    }
                }
            
        }

    except Exception as e:
        raise HTTPException(status_code=400,detail=f"server error {e}")
    
@auth_router.post("/signin")
async def signin(data: LoginPayload):
    print(data)
    user = await User.filter(email=data.email).first()
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="User Not found"
        )
    
    try:
        is_varified = ph.verify(user.password, data.password)
    except:
        raise HTTPException(
            status_code=400, 
            detail="Invalid email or password"
        )

    try:
        token = generate_user_token({ "id": user.id })
        return { 
            "success": True,
            "token": token,
            "user": {
                'name': user.name,
                'email': user.email,
                'type':user.type,
            },
            "detail":"Login Successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail="Authentication failed. Please try again."
        )

    


@auth_router.post("/update-profile")
async def update_profile(data: UpdateProfilePayload,current:Annotated[User,Depends(get_current_user)]):
    user, company  = current

    if await User.filter(email=data.email).first():
        if data.email != user.email:
            
            raise HTTPException(detail="Email already exists", status_code=400)
    if data.newPassword:
        try:
            ph.verify(user.password,data.password) # type: ignore
        except:
            raise HTTPException(status_code=403,detail="Current password is incorrect")
    try:
        if data.newPassword:
            hashed_password = ph.hash(data.newPassword)
            user.password = hashed_password
        user.name = data.name
        user.email = data.email
        await user.save()
        return {
            "success": True,
            "data": {
                "name": user.name,
                "email": user.email,
            },
            "detail": "Profile updated successfully"
        }
            
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=400)


@auth_router.get("/profile")
async def get_profile(current:Annotated[User,Depends(get_current_user)]):
    user, company  = current

    if not user:
        raise HTTPException(detail="Un Authenticated", status_code=401)
    return {
        "success": True,
        "data": {
            "name": user.name,
            "email": user.email,
            "type":user.type,
        },
        "detail": "Profile fetched successfully"
    }


@auth_router.get("/validate-token")
async def validate_me(current: Annotated[User, Depends(get_current_user)]):
    user, company  = current
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "success": True,
        "data": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "type": user.type,
        },
        "detail": "Token is valid. User authenticated successfully."
    }
