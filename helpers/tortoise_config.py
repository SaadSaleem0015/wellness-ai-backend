from dotenv import load_dotenv
load_dotenv()
from tortoise import Tortoise
from contextlib import asynccontextmanager
import os


db_url = os.getenv("DATABASE_URI")
if not db_url:
    raise ValueError("DATABASE_URI environment variable is not set.")


TORTOISE_CONFIG = {

    'connections': {
        'default': db_url
    },
    "apps": {
        "models": {
            "models": [
                "models.user",
                "models.code",
                "models.calendlytoken",
                "models.company",
                "models.lead",
                "models.purchased_number",
                "models.call_log",
                "models.assistant",
                "models.tool",
                "models.knowledge_base",
                "models.file",
                "models.schedule",
                "models.patient",
                "models.appointment",
                "aerich.models"
            ]
        }
    }
    }


@asynccontextmanager
async def lifespan(_):
    await Tortoise.init(config=TORTOISE_CONFIG)
    try:
        yield
    finally:
        await Tortoise.close_connections()