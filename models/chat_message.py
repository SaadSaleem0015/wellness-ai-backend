from tortoise import fields
from tortoise.models import Model
from datetime import datetime



class ChatMessage(Model):
    id = fields.IntField(primary_key=True, index=True)
    message = fields.TextField()
    answer = fields.TextField()
    created_at = fields.DatetimeField(default=datetime.utcnow, nullable=False)
    updated_at = fields.DatetimeField(default=datetime.utcnow, on_update=datetime.utcnow, nullable=False)
    chat = fields.ForeignKeyField('models.Chat', related_name='chat', on_delete=fields.CASCADE)