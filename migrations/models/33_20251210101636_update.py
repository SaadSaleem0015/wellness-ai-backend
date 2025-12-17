from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "generatedcontent" ADD "user_id" INT;
        ALTER TABLE "generatedcontent" ADD "voice_id" VARCHAR(255);
        ALTER TABLE "generatedcontent" ADD "heygen_video_id" VARCHAR(255);
        ALTER TABLE "generatedcontent" ADD "motion_prompt" TEXT;
        ALTER TABLE "generatedcontent" ADD "asset_id" INT;
        ALTER TABLE "generatedcontent" ADD "video_title" TEXT;
        ALTER TABLE "generatedcontent" ADD "company_id" INT;
        DROP TABLE IF EXISTS "customgeneratedvideo";
        ALTER TABLE "generatedcontent" ADD CONSTRAINT "fk_generate_uploaded_604ece87" FOREIGN KEY ("asset_id") REFERENCES "uploadedasset" ("id") ON DELETE CASCADE;
        ALTER TABLE "generatedcontent" ADD CONSTRAINT "fk_generate_company_76c5204b" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON DELETE CASCADE;
        ALTER TABLE "generatedcontent" ADD CONSTRAINT "fk_generate_user_0f6c332c" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "generatedcontent" DROP CONSTRAINT IF EXISTS "fk_generate_user_0f6c332c";
        ALTER TABLE "generatedcontent" DROP CONSTRAINT IF EXISTS "fk_generate_company_76c5204b";
        ALTER TABLE "generatedcontent" DROP CONSTRAINT IF EXISTS "fk_generate_uploaded_604ece87";
        ALTER TABLE "generatedcontent" DROP COLUMN "user_id";
        ALTER TABLE "generatedcontent" DROP COLUMN "voice_id";
        ALTER TABLE "generatedcontent" DROP COLUMN "heygen_video_id";
        ALTER TABLE "generatedcontent" DROP COLUMN "motion_prompt";
        ALTER TABLE "generatedcontent" DROP COLUMN "asset_id";
        ALTER TABLE "generatedcontent" DROP COLUMN "video_title";
        ALTER TABLE "generatedcontent" DROP COLUMN "company_id";"""
