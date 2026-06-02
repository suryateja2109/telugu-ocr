# Cloud Deployment Guide (24/7 Live Website)

Follow these steps to deploy your Telugu Digitized Book portal to the cloud so that it stays online 24/7.

---

## Step 1: Initialize Git and Push to GitHub

1. Open a terminal and run the following commands to initialize a git repository in this folder and push it to a new GitHub repository:
   ```bash
   cd /home/surya/project/telugu_db_solution
   git init
   git add .
   git commit -m "Initial commit of Telugu Digitized Book Solution"
   ```
2. Create a new repository on GitHub (e.g., named `telugu-doc-portal`). Do **not** initialize it with a README, license, or gitignore.
3. Link and push your local files:
   ```bash
   git branch -M main
   git remote add origin https://github.com/suryateja2109/telugu-doc-portal.git
   git push -u origin main
   ```
   *(Note: Replace the URL with your actual GitHub repository URL).*

---

## Step 2: Seed the Remote Database (Neon/Supabase)

Once you have created your free PostgreSQL database on Neon or Supabase and have the **connection string** (e.g., `postgresql://...`), run these commands from your local machine to populate the remote database:

1. **Initialize the database schema (create tables and search indexes)**:
   ```bash
   psql "YOUR_CONNECTION_STRING_HERE" -f /home/surya/project/telugu_db_solution/schema.sql
   ```
2. **Ingest document metadata, pages, text blocks, and images**:
   ```bash
   DATABASE_URL="YOUR_CONNECTION_STRING_HERE" python3 /home/surya/project/telugu_db_solution/db_loader.py --dir /home/surya/project/auto --doc-name "బాలగీతావళి (Telugu Poetry Reader)"
   ```

---

## Step 3: Deploy to Render (https://render.com)

1. Sign up/Log in to **Render** and click **New** ➔ **Web Service**.
2. Select your GitHub account and connect the `telugu-doc-portal` repository.
3. Configure the following build settings:
   *   **Runtime**: `Python`
   *   **Build Command**: `pip install -r requirements.txt`
   *   **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
4. Expand **Advanced** ➔ **Add Environment Variable**:
   *   **Key**: `DATABASE_URL`
   *   **Value**: *Your database connection URI (same as used in Step 2)*
5. Click **Create Web Service**.

Render will automatically pull the code, install dependencies, build the container, and host it. It will provide you with a permanent public HTTPS URL (e.g. `https://telugu-doc-portal.onrender.com`) that stays live 24/7.
