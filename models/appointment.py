from tortoise import fields
from tortoise.models import Model
from datetime import datetime
from enum import Enum


class AppointmentStatus(Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Appointment(Model):
    id = fields.IntField(primary_key=True)
    uuid = fields.CharField(max_length=255, unique=True)  # Calendly UUID
    patient = fields.ForeignKeyField("models.Patient", related_name="appointments")
    event_type_uri = fields.CharField(max_length=500)
    appointment_date = fields.DatetimeField()
    status = fields.CharEnumField(enum_type=AppointmentStatus, max_length=20, default=AppointmentStatus.ACTIVE)
    questions_answers = fields.JSONField(default=list)  # Store Q&A as JSON
    cancel_url = fields.CharField(max_length=500, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "appointments"
