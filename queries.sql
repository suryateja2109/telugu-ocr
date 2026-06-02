-- =====================================================================
-- Sample Search Queries for Telugu Document Database
-- =====================================================================

-- 1. Search for a Telugu word/phrase using Trigram Index (Matches grammatical variations and substrings)
-- This query searches for occurrences of the stem 'దేవు' (related to God: దేవుడు, దేవుని, దేవుఁడు)
-- It returns: Document Name, Page Number, Text Content, and Bounding Box coordinates
SELECT 
    d.document_name,
    p.page_number,
    tb.block_type,
    tb.text_content,
    tb.x1, 
    tb.y1, 
    tb.x2, 
    tb.y2
FROM text_blocks tb
JOIN pages p ON tb.page_id = p.page_id
JOIN documents d ON p.document_id = d.document_id
WHERE tb.text_content ILIKE '%దేవు%'
ORDER BY p.page_number, tb.text_block_id;


-- 2. Search for a Telugu word/phrase using Full-Text Search (FTS) Index
-- Optimized for exact token matches (using 'simple' English dictionary for tokenized Telugu text)
SELECT 
    p.page_number,
    tb.text_content,
    tb.x1, 
    tb.y1, 
    tb.x2, 
    tb.y2
FROM text_blocks tb
JOIN pages p ON tb.page_id = p.page_id
WHERE to_tsvector('simple', tb.text_content) @@ to_tsquery('simple', 'దేవుడు')
ORDER BY p.page_number;


-- 3. Retrieve all images associated with a specific Page (e.g., Page number 11)
-- Returns the image name, file path, bounding box coordinates, and checks if image binary data exists
SELECT 
    p.page_number,
    img.image_name,
    img.image_path,
    img.x1,
    img.y1,
    img.x2,
    img.y2,
    LENGTH(img.image_data) AS image_size_bytes
FROM images img
JOIN pages p ON img.page_id = p.page_id
WHERE p.page_number = 12  -- Note: 1-indexed page number (page_idx 11 is page_number 12)
ORDER BY img.image_id;


-- 4. Retrieve complete page contents (both Text and Images ordered by layout coordinates)
-- This allows reconstruction of the reading order of a page (e.g., Page number 13)
(
    SELECT 
        'text' AS type,
        tb.text_content AS content_summary,
        tb.x1, tb.y1, tb.x2, tb.y2
    FROM text_blocks tb
    JOIN pages p ON tb.page_id = p.page_id
    WHERE p.page_number = 13
)
UNION ALL
(
    SELECT 
        'image' AS type,
        img.image_name AS content_summary,
        img.x1, img.y1, img.x2, img.y2
    FROM images img
    JOIN pages p ON img.page_id = p.page_id
    WHERE p.page_number = 13
)
ORDER BY y1, x1; -- Order by vertical position then horizontal position (top-to-bottom layout)
