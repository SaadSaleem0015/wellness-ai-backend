from tortoise import fields
from tortoise.models import Model
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class UserType(Enum):
    ADMIN = "admin"
    USER = "user"

class User(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    type = fields.CharEnumField(enum_type=UserType, max_length=6, default=UserType.USER)
    email = fields.CharField(max_length=255)
    email_verified = fields.BooleanField(default=False)
    password = fields.CharField(max_length=255)
        
    main_admin = fields.BooleanField(default=False)
    team: fields.ReverseRelation["Team"]
    company = fields.ForeignKeyField("models.Company", null=True, related_name="users")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)




