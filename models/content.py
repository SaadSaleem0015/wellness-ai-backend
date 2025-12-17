from tortoise import fields
from tortoise.models import Model
from datetime import datetime

class GeneratedContent(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name = "customvideo", null = True)
    company = fields.ForeignKeyField("models.Company", related_name = "customvideo" , null = True)
    heygen_video_id = fields.CharField(max_length=255, null=True)  # returned from Heygen
    asset = fields.ForeignKeyField(
        "models.UploadedAsset",
        related_name="generated_videos", null=True
    )
    video_title = fields.TextField(null=True)           # c
    voice_id = fields.CharField(max_length=255, null=True)           # from request.voice_id
    motion_prompt = fields.TextField(null=True)           # c
    input_prompt = fields.TextField()
    generated_text = fields.TextField()
    content_type = fields.CharField(max_length=10)  # 'image' or 'video'
    image_url = fields.TextField(null=True)
    video_url = fields.TextField(null=True)
    created_at = fields.DatetimeField(default=datetime.utcnow, nullable=False)
    updated_at = fields.DatetimeField(default=datetime.utcnow, on_update=datetime.utcnow, nullable=False)