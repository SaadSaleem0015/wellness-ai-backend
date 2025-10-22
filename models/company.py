from tortoise.models import Model
from tortoise import fields

class Company(Model):
    id = fields.IntField(primary_key=True)
    company_name = fields.CharField(max_length=255, null=True)
    admin_name = fields.CharField(max_length=255, null=True)
    users: fields.ReverseRelation["User"]

   