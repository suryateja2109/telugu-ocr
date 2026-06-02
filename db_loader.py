#!/usr/bin/env python3
"""
Telugu Document DB Loader
Loads parsed OCR JSON and images into PostgreSQL.

Usage:
    python3 db_loader.py --dir /home/surya/project/auto --doc-name telugu.pdf
"""

import os
import sys
import json
import argparse
import psycopg2
import psycopg2.extras
from psycopg2 import sql

# Import configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import db_config


def get_connection():
    """Establish connection to PostgreSQL using config credentials."""
    if db_config.DATABASE_URL:
        return psycopg2.connect(db_config.DATABASE_URL)
    return psycopg2.connect(
        host=db_config.DB_HOST,
        port=db_config.DB_PORT,
        dbname=db_config.DB_NAME,
        user=db_config.DB_USER,
        password=db_config.DB_PASS
    )


def read_image_bytes(image_path_or_name, images_dir):
    """Read local image file as binary bytes for database storage."""
    if not image_path_or_name:
        return None
    
    filename = os.path.basename(image_path_or_name)
    full_path = os.path.join(images_dir, filename)
    
    if os.path.exists(full_path):
        try:
            with open(full_path, "rb") as f:
                return f.read()
        except Exception as e:
            print(f"  [Warning] Failed to read image file {full_path}: {e}")
            return None
    else:
        # Check parent dir as well
        alt_path = os.path.join(os.path.dirname(images_dir), filename)
        if os.path.exists(alt_path):
            try:
                with open(alt_path, "rb") as f:
                    return f.read()
            except Exception as e:
                print(f"  [Warning] Failed to read image file {alt_path}: {e}")
                return None
    return None


def process_detailed_json(conn, doc_id, data, images_dir):
    """Process telugu_content_list.json containing layout block detail."""
    cur = conn.cursor()
    
    # 1. Gather unique pages
    unique_page_indices = sorted(list(set(item["page_idx"] for item in data if "page_idx" in item)))
    page_id_map = {}
    
    print(f"  Inserting {len(unique_page_indices)} page metadata records...")
    for idx in unique_page_indices:
        page_num = idx + 1 # Convert 0-indexed to 1-indexed for standard page representation
        cur.execute(
            "INSERT INTO pages (document_id, page_number) VALUES (%s, %s) "
            "ON CONFLICT (document_id, page_number) DO UPDATE SET page_number = EXCLUDED.page_number "
            "RETURNING page_id;",
            (doc_id, page_num)
        )
        page_id = cur.fetchone()[0]
        page_id_map[idx] = page_id

    # 2. Parse text blocks and images
    text_blocks_batch = []
    images_batch = []
    
    for item in data:
        page_idx = item.get("page_idx")
        if page_idx is None or page_idx not in page_id_map:
            continue
        
        page_id = page_id_map[page_idx]
        block_type = item.get("type", "text")
        text_content = item.get("text", "")
        bbox = item.get("bbox", [0.0, 0.0, 0.0, 0.0])
        
        # Format bounding box coordinates safely
        if not isinstance(bbox, list) or len(bbox) < 4:
            bbox = [0.0, 0.0, 0.0, 0.0]
        x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        
        # If type is text or discarded or equation (with text content)
        if text_content and block_type in ("text", "discarded", "equation", "table"):
            text_blocks_batch.append((page_id, text_content, x1, y1, x2, y2, block_type))
            
        # If item has image path
        img_path = item.get("img_path", "")
        if img_path or block_type == "image":
            # Some equation blocks also have image paths
            img_name = os.path.basename(img_path) if img_path else f"page_{page_idx}_img.jpg"
            img_data = read_image_bytes(img_path, images_dir)
            images_batch.append((page_id, img_name, img_path or img_name, x1, y1, x2, y2, psycopg2.Binary(img_data) if img_data else None))

    # 3. Perform batch insertion for text blocks
    if text_blocks_batch:
        print(f"  Batch inserting {len(text_blocks_batch)} text blocks...")
        insert_text_query = """
            INSERT INTO text_blocks (page_id, text_content, x1, y1, x2, y2, block_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        psycopg2.extras.execute_batch(cur, insert_text_query, text_blocks_batch, page_size=200)

    # 4. Perform batch insertion for images
    if images_batch:
        print(f"  Batch inserting {len(images_batch)} images...")
        insert_image_query = """
            INSERT INTO images (page_id, image_name, image_path, x1, y1, x2, y2, image_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        psycopg2.extras.execute_batch(cur, insert_image_query, images_batch, page_size=100)

    cur.close()
    return len(unique_page_indices), len(text_blocks_batch), len(images_batch)


def process_flat_json(conn, doc_id, data, images_dir):
    """Process fallback pages_data.json containing flat page texts."""
    cur = conn.cursor()
    
    text_blocks_batch = []
    images_batch = []
    
    print(f"  Inserting {len(data)} page metadata records...")
    for page_item in data:
        page_num = page_item.get("page_number")
        if page_num is None:
            continue
            
        cur.execute(
            "INSERT INTO pages (document_id, page_number) VALUES (%s, %s) "
            "ON CONFLICT (document_id, page_number) DO UPDATE SET page_number = EXCLUDED.page_number "
            "RETURNING page_id;",
            (doc_id, page_num)
        )
        page_id = cur.fetchone()[0]
        
        # Add full page text as a block
        text_content = page_item.get("text_content", "")
        if text_content:
            text_blocks_batch.append((page_id, text_content, 0.0, 0.0, 0.0, 0.0, "text"))
            
        # Add page image if present
        img_name = page_item.get("image_filename", "")
        if img_name:
            img_data = read_image_bytes(img_name, images_dir)
            images_batch.append((page_id, img_name, img_name, 0.0, 0.0, 0.0, 0.0, psycopg2.Binary(img_data) if img_data else None))

    if text_blocks_batch:
        print(f"  Batch inserting {len(text_blocks_batch)} text blocks...")
        insert_text_query = """
            INSERT INTO text_blocks (page_id, text_content, x1, y1, x2, y2, block_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        psycopg2.extras.execute_batch(cur, insert_text_query, text_blocks_batch, page_size=200)

    if images_batch:
        print(f"  Batch inserting {len(images_batch)} images...")
        insert_image_query = """
            INSERT INTO images (page_id, image_name, image_path, x1, y1, x2, y2, image_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        psycopg2.extras.execute_batch(cur, insert_image_query, images_batch, page_size=100)

    cur.close()
    return len(data), len(text_blocks_batch), len(images_batch)


def main():
    parser = argparse.ArgumentParser(description="Ingest parsed Telugu document OCR into PostgreSQL.")
    parser.add_argument("--dir", default=db_config.JSON_DIR, help="Directory containing JSON files")
    parser.add_argument("--doc-name", default="telugu.pdf", help="Document Name metadata")
    args = parser.parse_args()

    print(f"=== Starting Ingestion from: {args.dir} ===")
    
    # 1. Locate JSON files in specified directory
    if not os.path.exists(args.dir):
        print(f"Error: Directory '{args.dir}' does not exist.")
        sys.exit(1)
        
    json_files = [f for f in os.listdir(args.dir) if f.endswith(".json")]
    if not json_files:
        print(f"Error: No JSON files found in '{args.dir}'.")
        sys.exit(1)
        
    print(f"Found JSON files: {json_files}")

    # Prioritize detailed layout list
    target_file = None
    is_detailed = True
    
    if "telugu_content_list.json" in json_files:
        target_file = "telugu_content_list.json"
    elif "pages_data.json" in json_files:
        target_file = "pages_data.json"
        is_detailed = False
    else:
        # Fallback to any json
        target_file = json_files[0]
        # Try to inspect structure
        try:
            with open(os.path.join(args.dir, target_file), "r", encoding="utf-8") as f:
                sample = json.load(f)
                if isinstance(sample, list) and len(sample) > 0:
                    if "page_idx" in sample[0]:
                        is_detailed = True
                    else:
                        is_detailed = False
        except Exception:
            is_detailed = True
            
    if not target_file:
        print("Error: Could not determine JSON file to parse.")
        sys.exit(1)

    json_path = os.path.join(args.dir, target_file)
    images_dir = os.path.join(args.dir, "images")
    
    print(f"Selected file: {target_file} (Mode: {'Detailed layout' if is_detailed else 'Flat page text'})")
    print(f"Images folder: {images_dir}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file {json_path}: {e}")
        sys.exit(1)

    # 2. Connect to Database
    print(f"Connecting to database {db_config.DB_NAME} on {db_config.DB_HOST}...")
    try:
        conn = get_connection()
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Please check database server status and credentials.")
        sys.exit(1)

    try:
        conn.autocommit = False
        cur = conn.cursor()
        
        # 3. Create or clean document entry to handle duplicates/re-ingest
        cur.execute("SELECT document_id FROM documents WHERE document_name = %s;", (args.doc_name,))
        row = cur.fetchone()
        if row:
            doc_id = row[0]
            print(f"Document '{args.doc_name}' already exists (ID: {doc_id}). Cleaning old records...")
            # Deleting from documents triggers cascade delete on pages, text_blocks, and images
            cur.execute("DELETE FROM documents WHERE document_id = %s;", (doc_id,))
            
        # Calculate total pages
        if is_detailed:
            total_pages = max(item.get("page_idx", 0) for item in data) + 1 if data else 0
        else:
            total_pages = len(data)
            
        cur.execute(
            "INSERT INTO documents (document_name, total_pages) VALUES (%s, %s) RETURNING document_id;",
            (args.doc_name, total_pages)
        )
        doc_id = cur.fetchone()[0]
        print(f"Registered document '{args.doc_name}' with ID: {doc_id}")

        # 4. Ingest pages, blocks, and images
        if is_detailed:
            inserted_pages, inserted_blocks, inserted_images = process_detailed_json(conn, doc_id, data, images_dir)
        else:
            inserted_pages, inserted_blocks, inserted_images = process_flat_json(conn, doc_id, data, images_dir)

        # Commit Transaction
        conn.commit()
        print("\n==========================================")
        print("  Ingestion Completed Successfully!")
        print("==========================================")
        print(f"  Document ID : {doc_id}")
        print(f"  Pages Loaded: {inserted_pages}")
        print(f"  Text Blocks : {inserted_blocks}")
        print(f"  Images Loaded: {inserted_images}")
        print("==========================================")
        
    except Exception as e:
        conn.rollback()
        print(f"\n[Error] Transaction rolled back due to error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
