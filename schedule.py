import asyncio
from datetime import datetime, timezone

from helpers.tortoise_config import TORTOISE_CONFIG
from tortoise import Tortoise
from models.schedule import Schedule
from models.lead import Lead
from models.assistant import Assistant
from models.purchased_number import PurchasedNumber
from helpers.vapi_helper import get_headers
import requests


async def init_db():
    await Tortoise.init(config=TORTOISE_CONFIG)


async def close_db():
    await Tortoise.close_connections()


async def process_due_schedules():
    now = datetime.now(timezone.utc)
    schedules = await Schedule.filter(is_processed=False, scheduled_at__lte=now).prefetch_related("assistant", "file")
    for sched in schedules:
        assistant = await Assistant.get(id=sched.assistant_id)
        print(leads)

        leads = await Lead.filter(file=sched.file).order_by("-created_at")
        print(leads)
        phone_number = None
        if assistant.attached_Number:
            phone = await PurchasedNumber.filter(phone_number=assistant.attached_Number).first()
            phone_number = phone.vapi_phone_uuid if phone else None

        completed = 0
        for lead in leads:
            try:
                if not phone_number:
                    continue
                mobile_no = lead.phone if lead.phone and lead.phone.startswith('+') else (f"+1{lead.phone}" if lead.phone else None)
                if not mobile_no:
                    continue
                
                payload = {
                    "name": "Scheduled Call",
                    "assistantId": assistant.vapi_assistant_id,
                    "customer": {
                        "numberE164CheckEnabled": True,
                        "extension": None,
                        "number": mobile_no,
                    },
                    "phoneNumberId": phone_number,
                }
                response = requests.post("https://api.vapi.ai/call", json=payload, headers=get_headers())
                if response.status_code in [200, 201]:
                    completed += 1
                    lead.call_count = (lead.call_count or 0) + 1
                    await lead.save()
            except Exception:
                continue

        sched.leads_completed = completed
        sched.is_processed = True
        await sched.save()


async def main_loop():
    await init_db()
    try:
        while True:
            await process_due_schedules()
            await asyncio.sleep(60 * 60)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main_loop())


