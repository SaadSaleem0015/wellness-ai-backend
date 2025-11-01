from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "chat" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "phone_number" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL
);
        CREATE TABLE IF NOT EXISTS "chatmessage" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "message" TEXT NOT NULL,
    "answer" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL,
    "chat_id" INT NOT NULL REFERENCES "chat" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "chatmessage";
        DROP TABLE IF EXISTS "chat";"""
