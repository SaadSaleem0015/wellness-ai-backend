from tortoise import fields
from tortoise.models import Model
from datetime import datetime



class Chat(Model):
    id = fields.IntField(primary_key=True, index=True)
    phone_number = fields.CharField(max_length=255, nullable=False)
    created_at = fields.DatetimeField(default=datetime.utcnow, nullable=False)
    updated_at = fields.DatetimeField(default=datetime.utcnow, on_update=datetime.utcnow, nullable=False)
    