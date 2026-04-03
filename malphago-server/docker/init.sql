-- MalPhaGo PostgreSQL initialization
-- This runs only on first container creation (empty pgdata volume)

SET client_encoding = 'UTF8';

-- Fuzzy text search for horse/jockey names
CREATE EXTENSION IF NOT EXISTS pg_trgm;
