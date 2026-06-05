-- Enable required extensions
-- These must be created here (before Alembic runs) because they require
-- superuser privileges, which the app user does not have.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- trigram search for keyword matching
CREATE EXTENSION IF NOT EXISTS "vector";   -- pgvector for similarity search

-- Set default timezone
SET timezone = 'UTC';
