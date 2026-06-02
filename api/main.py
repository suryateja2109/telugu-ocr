import os
import sys
import contextlib
import json
from fastapi import FastAPI, Query, HTTPException, Response, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

# Add parent directory to path to import db_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_config

app = FastAPI(
    title="Telugu Digitized Book API",
    description="A public REST API to search, browse, and download reconstructed Telugu book contents.",
    version="1.0.0"
)

# Enable CORS for public access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Templates
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

# Initialize Connection Pool
try:
    if db_config.DATABASE_URL:
        connection_pool = pool.SimpleConnectionPool(
            1, 10,
            dsn=db_config.DATABASE_URL
        )
    else:
        connection_pool = pool.SimpleConnectionPool(
            1, 10,
            host=db_config.DB_HOST,
            port=db_config.DB_PORT,
            dbname=db_config.DB_NAME,
            user=db_config.DB_USER,
            password=db_config.DB_PASS
        )
    print("Database connection pool initialized successfully.")
except Exception as e:
    print(f"Failed to initialize database pool: {e}")
    sys.exit(1)


@contextlib.contextmanager
def get_db_cursor():
    """Context manager to get a cursor from the connection pool."""
    conn = connection_pool.getconn()
    try:
        # Use RealDictCursor to return results as dictionaries
        cur = conn.cursor(cursor_factory=RealDictCursor)
        yield cur
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        connection_pool.putconn(conn)


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """Serve the Web Dashboard HTML page."""
    # Retrieve stats for the dashboard homepage
    stats = {}
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT count(*) as count FROM documents;")
            stats["total_documents"] = cur.fetchone()["count"]
            
            cur.execute("SELECT count(*) as count FROM pages;")
            stats["total_pages"] = cur.fetchone()["count"]
            
            cur.execute("SELECT count(*) as count FROM text_blocks;")
            stats["total_text_blocks"] = cur.fetchone()["count"]
            
            cur.execute("SELECT count(*) as count FROM images;")
            stats["total_images"] = cur.fetchone()["count"]
            
            cur.execute("SELECT document_name, total_pages, document_id FROM documents LIMIT 1;")
            doc = cur.fetchone()
            if doc:
                stats["document_name"] = doc["document_name"]
                stats["document_id"] = doc["document_id"]
            else:
                stats["document_name"] = "No documents loaded"
                stats["document_id"] = None
    except Exception as e:
        stats = {
            "total_documents": 0, "total_pages": 0, "total_text_blocks": 0, "total_images": 0,
            "document_name": "Database Connection Error", "document_id": None
        }
        print(f"Error loading stats for root: {e}")
        
    return templates.TemplateResponse(request, "index.html", {"stats": stats})


# =====================================================================
# REST API ENDPOINTS
# =====================================================================

@app.get("/api/stats")
def get_database_stats():
    """Retrieve summary statistics of the loaded document database."""
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT count(*) as count FROM documents;")
            docs_count = cur.fetchone()["count"]
            
            cur.execute("SELECT count(*) as count FROM pages;")
            pages_count = cur.fetchone()["count"]
            
            cur.execute("SELECT count(*) as count FROM text_blocks;")
            blocks_count = cur.fetchone()["count"]
            
            cur.execute("SELECT count(*) as count FROM images;")
            images_count = cur.fetchone()["count"]
            
            cur.execute("SELECT document_id, document_name, total_pages, created_at FROM documents;")
            docs = cur.fetchall()
            
            return {
                "status": "success",
                "documents_count": docs_count,
                "pages_count": pages_count,
                "text_blocks_count": blocks_count,
                "images_count": images_count,
                "documents": docs
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")


@app.get("/api/search")
def search_telugu_text(q: str = Query(..., min_length=1, description="Telugu text or phrase to search")):
    """
    Search for Telugu text across all documents.
    Uses the optimized GIN trigram index for partial and fuzzy matches.
    """
    try:
        with get_db_cursor() as cur:
            query = """
                SELECT 
                    d.document_name,
                    p.page_number,
                    p.page_id,
                    tb.text_block_id,
                    tb.text_content,
                    tb.block_type,
                    tb.x1, tb.y1, tb.x2, tb.y2
                FROM text_blocks tb
                JOIN pages p ON tb.page_id = p.page_id
                JOIN documents d ON p.document_id = d.document_id
                WHERE tb.text_content ILIKE %s
                ORDER BY p.page_number, tb.text_block_id;
            """
            cur.execute(query, (f"%{q}%",))
            results = cur.fetchall()
            
            # Format numeric bboxes for JSON
            for r in results:
                r["bbox"] = [float(r["x1"]), float(r["y1"]), float(r["x2"]), float(r["y2"])]
                del r["x1"], r["y1"], r["x2"], r["y2"]
                
            return {
                "query": q,
                "results_count": len(results),
                "results": results
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/pages")
def list_pages(document_id: int = None):
    """List all pages with their associated metadata and block counts."""
    try:
        with get_db_cursor() as cur:
            if document_id:
                query = """
                    SELECT p.page_id, p.page_number, p.document_id, d.document_name,
                           (SELECT count(*) FROM text_blocks WHERE page_id = p.page_id) as text_blocks_count,
                           (SELECT count(*) FROM images WHERE page_id = p.page_id) as images_count
                    FROM pages p
                    JOIN documents d ON p.document_id = d.document_id
                    WHERE p.document_id = %s
                    ORDER BY p.page_number;
                """
                cur.execute(query, (document_id,))
            else:
                query = """
                    SELECT p.page_id, p.page_number, p.document_id, d.document_name,
                           (SELECT count(*) FROM text_blocks WHERE page_id = p.page_id) as text_blocks_count,
                           (SELECT count(*) FROM images WHERE page_id = p.page_id) as images_count
                    FROM pages p
                    JOIN documents d ON p.document_id = d.document_id
                    ORDER BY d.document_name, p.page_number;
                """
                cur.execute(query)
            pages = cur.fetchall()
            return {"pages": pages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pages/{page_id}")
def get_page_details(page_id: int):
    """Retrieve detailed content of a single page (text blocks and images)."""
    try:
        with get_db_cursor() as cur:
            # Get page metadata
            cur.execute("""
                SELECT p.page_id, p.page_number, p.document_id, d.document_name 
                FROM pages p
                JOIN documents d ON p.document_id = d.document_id
                WHERE p.page_id = %s;
            """, (page_id,))
            page_meta = cur.fetchone()
            if not page_meta:
                raise HTTPException(status_code=404, detail="Page not found")
                
            # Get text blocks
            cur.execute("""
                SELECT text_block_id, text_content, block_type, x1, y1, x2, y2 
                FROM text_blocks 
                WHERE page_id = %s 
                ORDER BY y1, x1;
            """, (page_id,))
            text_blocks = cur.fetchall()
            for tb in text_blocks:
                tb["bbox"] = [float(tb["x1"]), float(tb["y1"]), float(tb["x2"]), float(tb["y2"])]
                del tb["x1"], tb["y1"], tb["x2"], tb["y2"]
                
            # Get images metadata
            cur.execute("""
                SELECT image_id, image_name, image_path, x1, y1, x2, y2 
                FROM images 
                WHERE page_id = %s 
                ORDER BY y1, x1;
            """, (page_id,))
            images = cur.fetchall()
            for img in images:
                img["bbox"] = [float(img["x1"]), float(img["y1"]), float(img["x2"]), float(img["y2"])]
                img["download_url"] = f"/api/images/{img['image_id']}"
                del img["x1"], img["y1"], img["x2"], img["y2"]
                
            return {
                "page_metadata": page_meta,
                "text_blocks": text_blocks,
                "images": images
            }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/images/{image_id}")
def stream_image(image_id: int):
    """Retrieve and stream raw binary JPEG image data directly from PostgreSQL."""
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT image_name, image_data FROM images WHERE image_id = %s;", (image_id,))
            row = cur.fetchone()
            if not row or not row["image_data"]:
                raise HTTPException(status_code=4404, detail="Image binary not found in database")
                
            image_name = row["image_name"]
            binary_data = bytes(row["image_data"])
            
            return Response(
                content=binary_data,
                media_type="image/jpeg",
                headers={
                    "Content-Disposition": f"inline; filename={image_name}",
                    "Cache-Control": "public, max-age=86400"  # Cache for 24 hours
                }
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# DOWNLOAD ENDPOINTS
# =====================================================================

@app.get("/api/download/all")
def download_full_database_json():
    """Download the entire database content (excluding raw binary blobs) as a structured JSON file."""
    try:
        export_data = {"documents": []}
        with get_db_cursor() as cur:
            # 1. Fetch documents
            cur.execute("SELECT document_id, document_name, total_pages, created_at FROM documents;")
            documents = cur.fetchall()
            
            for doc in documents:
                doc_id = doc["document_id"]
                doc_record = {
                    "document_name": doc["document_name"],
                    "total_pages": doc["total_pages"],
                    "created_at": str(doc["created_at"]),
                    "pages": []
                }
                
                # 2. Fetch pages for this document
                cur.execute("SELECT page_id, page_number FROM pages WHERE document_id = %s ORDER BY page_number;", (doc_id,))
                pages = cur.fetchall()
                
                for pg in pages:
                    pg_id = pg["page_id"]
                    page_record = {
                        "page_number": pg["page_number"],
                        "text_blocks": [],
                        "images": []
                    }
                    
                    # 3. Fetch text blocks
                    cur.execute("SELECT text_content, block_type, x1, y1, x2, y2 FROM text_blocks WHERE page_id = %s ORDER BY y1, x1;", (pg_id,))
                    tbs = cur.fetchall()
                    for tb in tbs:
                        page_record["text_blocks"].append({
                            "type": tb["block_type"],
                            "text": tb["text_content"],
                            "bbox": [float(tb["x1"]), float(tb["y1"]), float(tb["x2"]), float(tb["y2"])]
                        })
                        
                    # 4. Fetch images metadata (no binary data to keep JSON light)
                    cur.execute("SELECT image_id, image_name, image_path, x1, y1, x2, y2 FROM images WHERE page_id = %s ORDER BY y1, x1;", (pg_id,))
                    imgs = cur.fetchall()
                    for img in imgs:
                        page_record["images"].append({
                            "image_id": img["image_id"],
                            "image_name": img["image_name"],
                            "image_path": img["image_path"],
                            "bbox": [float(img["x1"]), float(img["y1"]), float(img["x2"]), float(img["y2"])],
                            "api_url": f"/api/images/{img['image_id']}"
                        })
                        
                    doc_record["pages"].append(page_record)
                export_data["documents"].append(doc_record)
                
        # Return as JSON file attachment
        json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=telugu_database_export.json"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database export failed: {str(e)}")


@app.get("/api/download/text")
def download_full_book_text():
    """Download the concatenated text content of the entire document book as a UTF-8 text file."""
    try:
        full_text = []
        with get_db_cursor() as cur:
            # Get pages ordered by page number
            cur.execute("""
                SELECT p.page_id, p.page_number, d.document_name
                FROM pages p
                JOIN documents d ON p.document_id = d.document_id
                ORDER BY p.page_number;
            """)
            pages = cur.fetchall()
            
            if not pages:
                raise HTTPException(status_code=404, detail="No pages found to export.")
                
            full_text.append(f"==================================================")
            full_text.append(f" BOOK: {pages[0]['document_name']}")
            full_text.append(f"==================================================\n\n")
            
            for pg in pages:
                full_text.append(f"--- PAGE {pg['page_number']} ---")
                
                # Fetch text blocks for this page
                cur.execute("""
                    SELECT text_content 
                    FROM text_blocks 
                    WHERE page_id = %s AND block_type IN ('text', 'equation')
                    ORDER BY y1, x1;
                """, (pg["page_id"],))
                blocks = cur.fetchall()
                
                page_text = "\n".join(b["text_content"] for b in blocks if b["text_content"])
                full_text.append(page_text)
                full_text.append("\n\n")
                
        text_content = "\n".join(full_text)
        return Response(
            content=text_content,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=telugu_book_fulltext.txt"
            }
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/page/{page_id}/text")
def download_page_text(page_id: int):
    """Download a single page's text content as a text file."""
    try:
        with get_db_cursor() as cur:
            # Verify page and get number
            cur.execute("SELECT page_number FROM pages WHERE page_id = %s;", (page_id,))
            page_row = cur.fetchone()
            if not page_row:
                raise HTTPException(status_code=404, detail="Page not found")
            page_number = page_row["page_number"]
            
            # Fetch text blocks
            cur.execute("""
                SELECT text_content 
                FROM text_blocks 
                WHERE page_id = %s AND block_type IN ('text', 'equation')
                ORDER BY y1, x1;
            """, (page_id,))
            blocks = cur.fetchall()
            
            text_lines = [f"--- PAGE {page_number} ---"]
            for b in blocks:
                if b["text_content"]:
                    text_lines.append(b["text_content"])
                    
            text_content = "\n".join(text_lines)
            return Response(
                content=text_content,
                media_type="text/plain; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename=page_{page_number}_text.txt"
                }
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/db")
def download_database_dump():
    """Download the binary PostgreSQL database dump file."""
    dump_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "telugu_doc_db.dump")
    if not os.path.exists(dump_path):
        raise HTTPException(status_code=404, detail="Database dump file not found")
    return FileResponse(
        path=dump_path,
        media_type="application/octet-stream",
        filename="telugu_doc_db.dump"
    )


@app.get("/api/download/pdf/original")
def download_original_pdf():
    """Download the original scanned PDF."""
    pdf_path = "/home/surya/project/telugu.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Original scanned PDF not found")
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename="telugu.pdf"
    )


@app.get("/api/download/pdf/reconstructed")
def download_reconstructed_pdf():
    """Download the reconstructed searchable PDF."""
    pdf_path = "/home/surya/project/construct.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Reconstructed PDF not found")
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename="construct.pdf"
    )


@app.get("/api/download/docx/reconstructed")
def download_reconstructed_docx():
    """Download the reconstructed Word Document."""
    docx_path = "/home/surya/project/construct.docx"
    if not os.path.exists(docx_path):
        raise HTTPException(status_code=404, detail="Reconstructed Word Document not found")
    return FileResponse(
        path=docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="construct.docx"
    )
