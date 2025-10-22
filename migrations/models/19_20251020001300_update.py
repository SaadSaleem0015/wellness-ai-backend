from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "appointments";
        DROP TABLE IF EXISTS "patients";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
