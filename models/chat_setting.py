from tortoise import fields
from tortoise.models import Model
from datetime import datetime



class ChatSetting(Model):
    id = fields.IntField(primary_key=True, index=True)
    prompt = fields.TextField()
    model = fields.TextField()
    openai_key = fields.TextField()
    created_at = fields.DatetimeField(default=datetime.utcnow, nullable=False)
    updated_at = fields.DatetimeField(default=datetime.utcnow, on_update=datetime.utcnow, nullable=False)