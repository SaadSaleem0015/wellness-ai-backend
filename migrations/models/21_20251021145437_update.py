from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "file_metadata" RENAME TO "knowledgebase";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "knowledgebase" RENAME TO "file_metadata";"""
