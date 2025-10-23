from tortoise.models import Model
from tortoise import fields

class Lead(Model):
    id = fields.IntField(primary_key=True)
    file = fields.ForeignKeyField("models.File", related_name = "leads", null = True)
    name = fields.CharField(max_length=255,  null = True)
    email = fields.CharField(max_length=255, null = True)
    phone = fields.CharField(max_length=255,  null = True)
    source = fields.CharField(max_length=255,  null = True)
    city = fields.CharField(max_length=255,  null = True)
    state = fields.CharField(max_length=255,  null = True)
    country = fields.CharField(max_length=255,  null = True)
    is_called = fields.BooleanField(default = False)
    ghl_id = fields.TextField(null = True)
    add_date = fields.DateField( null = True)
    other_data = fields.JSONField(null=True) 
    tags = fields.JSONField(null=True) 
    location_id  = fields.TextField(null = True)
    last_called_at = fields.DatetimeField(null = True)  
    call_count = fields.IntField(null = True , default = 0) 
    deleted = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)