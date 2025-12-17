from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "clinichoursresponse" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "day_of_week" INT NOT NULL,
    "is_open" BOOL NOT NULL DEFAULT True,
    "opening_time" TIMETZ,
    "closing_time" TIMETZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "clinichoursresponse"."day_of_week" IS '0=Monday, 1=Tuesday, ..., 6=Sunday';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "clinichoursresponse";"""
