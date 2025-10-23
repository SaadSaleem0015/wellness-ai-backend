from fastapi import FastAPI
from datetime import datetime
from tortoise import Tortoise, fields
from tortoise.models import Model
from tortoise.contrib.fastapi import register_tortoise

class Knowledgebase(Model):
    id = fields.IntField(pk=True)
    vapi_id = fields.CharField(max_length=255, null=True)
    vapi_tool_id = fields.CharField(max_length=255, null=True)
    filename = fields.CharField(max_length=255) 
    original_filename = fields.CharField(max_length=255)  
    upload_date = fields.DatetimeField(default=datetime.utcnow)
    file_format = fields.CharField(max_length=50)
    user=fields.ForeignKeyField("models.User", related_name="file") 
    company=fields.ForeignKeyField("models.Company", related_name="files") 