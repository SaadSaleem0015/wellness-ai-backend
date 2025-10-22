from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "assistant" ADD "company_id" INT NOT NULL;
        ALTER TABLE "assistant" ADD CONSTRAINT "fk_assistan_company_10bcb277" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "assistant" DROP CONSTRAINT IF EXISTS "fk_assistan_company_10bcb277";
        ALTER TABLE "assistant" DROP COLUMN "company_id";"""
