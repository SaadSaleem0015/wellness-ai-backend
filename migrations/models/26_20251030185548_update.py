from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "availabilityblock" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "date" VARCHAR(10) NOT NULL,
    "blocked_slots" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "availabilityblock"."date" IS 'YYYY-MM-DD';
COMMENT ON COLUMN "availabilityblock"."blocked_slots" IS '[\"09:00\", \"09:15\", ..., \"16:45\"] (24h format)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "availabilityblock";"""
