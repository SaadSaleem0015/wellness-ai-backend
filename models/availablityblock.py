from tortoise.models import Model
from tortoise import fields
from typing import List

class AvailabilityBlock(Model):
    id: int = fields.IntField(pk=True)
    date: str = fields.CharField(max_length=10, description="YYYY-MM-DD")
    blocked_slots: List[str] = fields.JSONField(description='["09:00", "09:15", ..., "16:45"] (24h format)')
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)