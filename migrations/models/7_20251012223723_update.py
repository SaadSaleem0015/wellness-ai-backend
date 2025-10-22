from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "purchasednumber" ADD "company_id" INT NOT NULL;
        ALTER TABLE "purchasednumber" ADD CONSTRAINT "fk_purchase_company_71ca19a2" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "purchasednumber" DROP CONSTRAINT IF EXISTS "fk_purchase_company_71ca19a2";
        ALTER TABLE "purchasednumber" DROP COLUMN "company_id";"""
