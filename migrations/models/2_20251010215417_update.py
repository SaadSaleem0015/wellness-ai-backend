from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "main_admin" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "user" ADD "company_id" INT;
        CREATE TABLE IF NOT EXISTS "company" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "company_name" VARCHAR(255),
    "admin_name" VARCHAR(255)
);
        CREATE TABLE IF NOT EXISTS "lead" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "add_date" DATE NOT NULL,
    "phone" VARCHAR(255) NOT NULL,
    "other_data" JSONB,
    "last_called_at" TIMESTAMPTZ,
    "call_count" INT DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
        CREATE TABLE IF NOT EXISTS "purchasednumber" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "phone_number" VARCHAR(20) NOT NULL,
    "friendly_name" VARCHAR(255),
    "region" VARCHAR(255),
    "postal_code" VARCHAR(20),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "attached_assistant" INT,
    "vapi_phone_uuid" VARCHAR(255),
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "calllog" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "lead_id" INT,
    "call_started_at" TIMESTAMPTZ,
    "customer_number" VARCHAR(100),
    "customer_name" VARCHAR(100),
    "call_id" VARCHAR(1000),
    "cost" DECIMAL(10,2),
    "call_ended_at" TIMESTAMPTZ,
    "call_ended_reason" VARCHAR(100),
    "call_duration" DOUBLE PRECISION,
    "is_transferred" BOOL DEFAULT False,
    "status" VARCHAR(100),
    "criteria_satisfied" BOOL DEFAULT False,
    "recording_url" VARCHAR(1000),
    "transcript" TEXT,
    "company_id" INT NOT NULL REFERENCES "company" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "assistant" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "vapi_assistant_id" VARCHAR(255),
    "name" VARCHAR(255) NOT NULL,
    "provider" VARCHAR(255) NOT NULL,
    "first_message" VARCHAR(255) NOT NULL,
    "model" VARCHAR(255) NOT NULL,
    "systemPrompt" TEXT NOT NULL,
    "leadsfile" JSONB,
    "temperature" DOUBLE PRECISION,
    "maxTokens" INT,
    "transcribe_provider" VARCHAR(255),
    "transcribe_language" VARCHAR(255),
    "transcribe_model" VARCHAR(255),
    "voice_provider" VARCHAR(255),
    "voice" VARCHAR(255),
    "forwardingPhoneNumber" VARCHAR(255),
    "endCallPhrases" JSONB,
    "attached_Number" VARCHAR(255),
    "vapi_phone_uuid" VARCHAR(255),
    "success_evalution" TEXT,
    "voice_model" TEXT,
    "languages" JSONB,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "tool" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "credentialId" VARCHAR(255),
    "orgId" VARCHAR(255),
    "vapi_id" VARCHAR(255) NOT NULL UNIQUE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
        CREATE TABLE IF NOT EXISTS "file_metadata" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "vapi_id" VARCHAR(255),
    "filename" VARCHAR(255) NOT NULL,
    "original_filename" VARCHAR(255) NOT NULL,
    "upload_date" TIMESTAMPTZ NOT NULL,
    "file_format" VARCHAR(50) NOT NULL,
    "company_id" INT NOT NULL REFERENCES "company" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
        ALTER TABLE "user" ADD CONSTRAINT "fk_user_company_164e84ed" FOREIGN KEY ("company_id") REFERENCES "company" ("id") ON DELETE CASCADE;
        CREATE TABLE "assistant_file_metadata" (
    "assistant_id" INT NOT NULL REFERENCES "assistant" ("id") ON DELETE CASCADE,
    "knowledgebase_id" INT NOT NULL REFERENCES "file_metadata" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" DROP CONSTRAINT IF EXISTS "fk_user_company_164e84ed";
        ALTER TABLE "user" DROP COLUMN "main_admin";
        ALTER TABLE "user" DROP COLUMN "company_id";
        DROP TABLE IF EXISTS "company";
        DROP TABLE IF EXISTS "calllog";
        DROP TABLE IF EXISTS "purchasednumber";
        DROP TABLE IF EXISTS "lead";
        DROP TABLE IF EXISTS "tool";
        DROP TABLE IF EXISTS "file_metadata";
        DROP TABLE IF EXISTS "assistant";"""
