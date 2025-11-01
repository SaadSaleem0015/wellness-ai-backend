from tortoise import fields
from tortoise.models import Model
from datetime import datetime

class GeneratedContent(Model):
    id = fields.IntField(pk=True)
    input_prompt = fields.TextField()
    generated_text = fields.TextField()
    content_type = fields.CharField(max_length=10)  # 'image' or 'video'
    image_url = fields.TextField(null=True)
    video_url = fields.TextField(null=True)
    created_at = fields.DatetimeField(default=datetime.utcnow, nullable=False)
    updated_at = fields.DatetimeField(default=datetime.utcnow, on_update=datetime.utcnow, nullable=False)