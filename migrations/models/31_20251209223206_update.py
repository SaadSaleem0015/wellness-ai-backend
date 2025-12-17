from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "customgeneratedvideo" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "script" TEXT NOT NULL,
    "voice_id" VARCHAR(255) NOT NULL,
    "motion_prompt" TEXT,
    "heygen_video_id" VARCHAR(255),
    "status" VARCHAR(50) NOT NULL DEFAULT 'pending',
    "video_url" VARCHAR(500),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "asset_id" INT NOT NULL REFERENCES "uploadedasset" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "customgeneratedvideo";"""
