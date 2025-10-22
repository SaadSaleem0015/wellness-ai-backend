from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "lead" DROP CONSTRAINT IF EXISTS "fk_lead_file_e9dd8bc4";
        ALTER TABLE "lead" RENAME COLUMN "File_id" TO "file_id";
        ALTER TABLE "lead" ADD CONSTRAINT "fk_lead_file_fc03a0bc" FOREIGN KEY ("file_id") REFERENCES "file" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "lead" DROP CONSTRAINT IF EXISTS "fk_lead_file_fc03a0bc";
        ALTER TABLE "lead" RENAME COLUMN "file_id" TO "File_id";
        ALTER TABLE "lead" ADD CONSTRAINT "fk_lead_file_e9dd8bc4" FOREIGN KEY ("File_id") REFERENCES "file" ("id") ON DELETE CASCADE;"""
