from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "lead" ADD "location_id" TEXT;
        ALTER TABLE "lead" ADD "country" VARCHAR(255);
        ALTER TABLE "lead" ADD "tags" JSONB;
        ALTER TABLE "lead" ADD "city" VARCHAR(255);
        ALTER TABLE "lead" ADD "ghl_id" TEXT;
        ALTER TABLE "lead" ADD "state" VARCHAR(255);
        ALTER TABLE "lead" ADD "source" VARCHAR(255);
        ALTER TABLE "lead" ALTER COLUMN "name" DROP NOT NULL;
        ALTER TABLE "lead" ALTER COLUMN "add_date" DROP NOT NULL;
        ALTER TABLE "lead" ALTER COLUMN "email" DROP NOT NULL;
        ALTER TABLE "lead" ALTER COLUMN "phone" DROP NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "lead" DROP COLUMN "location_id";
        ALTER TABLE "lead" DROP COLUMN "country";
        ALTER TABLE "lead" DROP COLUMN "tags";
        ALTER TABLE "lead" DROP COLUMN "city";
        ALTER TABLE "lead" DROP COLUMN "ghl_id";
        ALTER TABLE "lead" DROP COLUMN "state";
        ALTER TABLE "lead" DROP COLUMN "source";
        ALTER TABLE "lead" ALTER COLUMN "name" SET NOT NULL;
        ALTER TABLE "lead" ALTER COLUMN "add_date" SET NOT NULL;
        ALTER TABLE "lead" ALTER COLUMN "email" SET NOT NULL;
        ALTER TABLE "lead" ALTER COLUMN "phone" SET NOT NULL;"""
