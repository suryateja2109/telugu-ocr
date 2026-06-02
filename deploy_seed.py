import os
import sys
import psycopg2
import subprocess

def main():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("DATABASE_URL env variable not found. Skipping seeding.")
        sys.exit(0)

    print("Connecting to database to check schema...")
    try:
        # Establish connection
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if documents table exists and has rows
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'documents'
            );
        """)
        table_exists = cur.fetchone()[0]
        
        has_rows = False
        if table_exists:
            try:
                cur.execute("SELECT COUNT(*) FROM documents;")
                has_rows = cur.fetchone()[0] > 0
            except Exception:
                has_rows = False
             
        if not table_exists or not has_rows:
            print("Database is empty or schema is missing. Initializing schema...")
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            
            # Execute schema queries
            cur.execute(schema_sql)
            print("Schema initialized successfully.")
            
            # Run db_loader
            print("Running db_loader to seed layout data and images...")
            loader_path = os.path.join(os.path.dirname(__file__), "db_loader.py")
            subprocess.run([sys.executable, loader_path, "--dir", "./data"], check=True)
            print("Database seeded successfully.")
        else:
            print("Database already contains data. Skipping seeding.")
             
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Warning: Exception encountered during database seeding: {e}")
        # Return success to allow the Web Service to boot regardless
        sys.exit(0)

if __name__ == "__main__":
    main()
