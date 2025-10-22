from tortoise.models import Model
from tortoise import fields


class Schedule(Model):
    id = fields.IntField(primary_key=True)
    assistant = fields.ForeignKeyField("models.Assistant", related_name="schedules")
    file = fields.ForeignKeyField("models.File", related_name="schedules")
    scheduled_at = fields.DatetimeField()
    is_processed = fields.BooleanField(default=False)
    total_leads = fields.IntField(default=0)
    leads_completed = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


