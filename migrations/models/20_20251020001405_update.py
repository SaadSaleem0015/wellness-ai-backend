from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "patients" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "phone" VARCHAR(20) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
        CREATE TABLE IF NOT EXISTS "appointments" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "uuid" VARCHAR(255) NOT NULL UNIQUE,
    "event_type_uri" VARCHAR(500) NOT NULL,
    "appointment_date" TIMESTAMPTZ NOT NULL,
    "status" VARCHAR(20) NOT NULL DEFAULT 'active',
    "questions_answers" JSONB NOT NULL,
    "cancel_url" VARCHAR(500),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "patient_id" INT NOT NULL REFERENCES "patients" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "appointments"."status" IS 'ACTIVE: active\nCANCELED: canceled\nCOMPLETED: completed\nNO_SHOW: no_show';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "appointments";
        DROP TABLE IF EXISTS "patients";"""
