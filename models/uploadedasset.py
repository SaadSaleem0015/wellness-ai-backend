from tortoise import fields
from tortoise.models import Model


class UploadedAsset(Model):
    id = fields.IntField(primary_key=True)

    name = fields.CharField(max_length=255)

    # New fields you are using:
    heygen_id = fields.CharField(max_length=255, null=True)
    image_key = fields.CharField(max_length=255, null=True)
    file_type = fields.CharField(max_length=50, null=True)
    url = fields.CharField(max_length=500, null=True)

    user = fields.ForeignKeyField("models.User", related_name="assets")
    company = fields.ForeignKeyField("models.Company", related_name="asset")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
