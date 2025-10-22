from tortoise.models import Model
from tortoise import fields
from datetime import datetime

class CalendlyToken(Model):
    id = fields.IntField(pk=True)  # always 1 (single account)
    access_token = fields.CharField(max_length=255)
    refresh_token = fields.CharField(max_length=255)
    expires_at = fields.DatetimeField()  # when the access_token will expire
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
