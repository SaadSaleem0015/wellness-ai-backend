from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "assistant" RENAME COLUMN "languages" TO "tools";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "assistant" RENAME COLUMN "tools" TO "languages";"""
