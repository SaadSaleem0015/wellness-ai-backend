from tortoise import fields
from tortoise.models import Model
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.appointment import Appointment


class Patient(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    email = fields.CharField(max_length=255)
    phone = fields.CharField(max_length=20)  # Unique identifier
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    # Relationship to appointments
    appointments: fields.ReverseRelation["Appointment"]
    
    class Meta:
        table = "patients"
