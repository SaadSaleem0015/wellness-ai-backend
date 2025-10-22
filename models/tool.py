from tortoise.models import Model
from tortoise import fields

class Tool(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    credentialId = fields.CharField(max_length=255, null=True)
    orgId = fields.CharField(max_length=255, null=True)
    vapi_id = fields.CharField(max_length=255, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
