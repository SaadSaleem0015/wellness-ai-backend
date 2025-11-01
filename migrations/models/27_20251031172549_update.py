from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "generatedcontent" ADD "video_url" TEXT;
        ALTER TABLE "generatedcontent" ADD "content_type" VARCHAR(10) NOT NULL;
        ALTER TABLE "generatedcontent" ALTER COLUMN "image_url" DROP NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "generatedcontent" DROP COLUMN "video_url";
        ALTER TABLE "generatedcontent" DROP COLUMN "content_type";
        ALTER TABLE "generatedcontent" ALTER COLUMN "image_url" SET NOT NULL;"""
