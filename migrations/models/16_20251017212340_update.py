from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "schedule" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "scheduled_at" TIMESTAMPTZ NOT NULL,
    "is_processed" BOOL NOT NULL DEFAULT False,
    "total_leads" INT NOT NULL DEFAULT 0,
    "leads_completed" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "assistant_id" INT NOT NULL REFERENCES "assistant" ("id") ON DELETE CASCADE,
    "file_id" INT NOT NULL REFERENCES "file" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "schedule";"""
