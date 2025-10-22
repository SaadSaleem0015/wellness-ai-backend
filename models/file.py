from tortoise import fields
from tortoise.models import Model


class File(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(255)
    user = fields.ForeignKeyField("models.User", related_name = "lead")
    company = fields.ForeignKeyField("models.Company", related_name = "leads")
    leads: fields.ReverseRelation['Lead']
    type = fields.CharField(255)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

