from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "lead" ADD "File_id" INT NOT NULL;
        ALTER TABLE "lead" ADD CONSTRAINT "fk_lead_file_e9dd8bc4" FOREIGN KEY ("File_id") REFERENCES "file" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "lead" DROP CONSTRAINT IF EXISTS "fk_lead_file_e9dd8bc4";
        ALTER TABLE "lead" DROP COLUMN "File_id";"""
