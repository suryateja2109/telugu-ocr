-- ==========================================
-- PostgreSQL Schema for Telugu Document DB
-- ==========================================

-- Drop existing tables to apply schema modifications cleanly
DROP TABLE IF EXISTS text_blocks CASCADE;
DROP TABLE IF EXISTS images CASCADE;
DROP TABLE IF EXISTS pages CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- 1. Create Documents Table
CREATE TABLE IF NOT EXISTS documents (
    document_id SERIAL PRIMARY KEY,
    document_name VARCHAR(255) NOT NULL UNIQUE,
    total_pages INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create Pages Table
CREATE TABLE IF NOT EXISTS pages (
    page_id SERIAL PRIMARY KEY,
    document_id INT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    page_number INT NOT NULL, -- 1-indexed page number
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_document_page UNIQUE (document_id, page_number)
);

-- 3. Create Images Table
CREATE TABLE IF NOT EXISTS images (
    image_id SERIAL PRIMARY KEY,
    page_id INT NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
    image_name VARCHAR(255) NOT NULL,
    image_path VARCHAR(512) NOT NULL,
    x1 NUMERIC(8,2) NOT NULL,
    y1 NUMERIC(8,2) NOT NULL,
    x2 NUMERIC(8,2) NOT NULL,
    y2 NUMERIC(8,2) NOT NULL,
    image_data BYTEA, -- Holds raw binary bytes of the image
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create Text Blocks Table
CREATE TABLE IF NOT EXISTS text_blocks (
    text_block_id SERIAL PRIMARY KEY,
    page_id INT NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
    text_content TEXT NOT NULL,
    x1 NUMERIC(8,2) NOT NULL,
    y1 NUMERIC(8,2) NOT NULL,
    x2 NUMERIC(8,2) NOT NULL,
    y2 NUMERIC(8,2) NOT NULL,
    block_type VARCHAR(50) NOT NULL, -- e.g., 'text', 'discarded', 'equation', 'text_inside_image'
    associated_image_id INT REFERENCES images(image_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- Performance and Search Indexing
-- ==========================================

-- Enable the pg_trgm extension for Trigram indexing (essential for partial, fuzzy, and substring searches in Telugu)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create GIN index on text_content using trigram operations (matches LIKE '%word%')
CREATE INDEX IF NOT EXISTS idx_text_blocks_content_trgm ON text_blocks USING gin (text_content gin_trgm_ops);

-- Create GIN index for Full-Text Search using 'simple' configuration (tokenized text search)
CREATE INDEX IF NOT EXISTS idx_text_blocks_content_fts ON text_blocks USING GIN (to_tsvector('simple', text_content));

-- Create B-Tree indexes on foreign keys and commonly searched columns
CREATE INDEX IF NOT EXISTS idx_pages_document_id ON pages(document_id);
CREATE INDEX IF NOT EXISTS idx_text_blocks_page_id ON text_blocks(page_id);
CREATE INDEX IF NOT EXISTS idx_images_page_id ON images(page_id);
CREATE INDEX IF NOT EXISTS idx_pages_page_number ON pages(page_number);
CREATE INDEX IF NOT EXISTS idx_text_blocks_associated_image_id ON text_blocks(associated_image_id);
