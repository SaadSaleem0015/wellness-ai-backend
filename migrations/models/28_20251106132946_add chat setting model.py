from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "chatsetting" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "prompt" TEXT NOT NULL,
    "model" TEXT NOT NULL,
    "openai_key" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "chatsetting";"""
