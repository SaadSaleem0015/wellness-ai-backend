from tortoise import fields
from tortoise.models import Model
from datetime import datetime

class ClinicHoursResponse(Model):
    id = fields.IntField(pk=True)
    day_of_week = fields.IntField(description="0=Monday, 1=Tuesday, ..., 6=Sunday")
    is_open = fields.BooleanField(default=True)
    opening_time = fields.TimeField(null=True)
    closing_time = fields.TimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)