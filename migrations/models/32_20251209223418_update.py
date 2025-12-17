from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "customgeneratedvideo" ADD "company_id" INT NOT NULL;
        ALTER TABLE "customgeneratedvideo" ADD "user_id" INT NOT NULL;
        ALTER TABLE "customgeneratedvideo" ADD CONSTRAINT "fk_customge_user_70f70b39" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE;
        ALTER TABLE "customgeneratedvideo" ADD CONSTRAINT "fk_customge_company_1c9f3585" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "customgeneratedvideo" DROP CONSTRAINT IF EXISTS "fk_customge_company_1c9f3585";
        ALTER TABLE "customgeneratedvideo" DROP CONSTRAINT IF EXISTS "fk_customge_user_70f70b39";
        ALTER TABLE "customgeneratedvideo" DROP COLUMN "company_id";
        ALTER TABLE "customgeneratedvideo" DROP COLUMN "user_id";"""
