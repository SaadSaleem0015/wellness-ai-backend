from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "purchasednumber" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "phone_number" VARCHAR(20) NOT NULL,
    "friendly_name" VARCHAR(255),
    "region" VARCHAR(255),
    "postal_code" VARCHAR(20),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "attached_assistant" INT,
    "vapi_phone_uuid" VARCHAR(255),
    "company_id" INT NOT NULL REFERENCES "company" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "purchasednumber";"""
