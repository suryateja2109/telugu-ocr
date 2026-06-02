# Cloud Deployment Guide (24/7 Live Website on Render)

We have prepared the repository to be self-contained and ready for automatic 1-click deployment to **Render** using a Blueprint (`render.yaml`).

---

## Step 1: Initialize Git and Push to GitHub

1. Open a terminal and run the following commands to stage all files, commit them, and link them to a new GitHub repository:
   ```bash
   cd /home/surya/project/telugu_db_solution
   git init
   git add .
   git commit -m "Configure self-contained cloud deployment with Render Blueprint"
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

## Step 2: Deploy to Render

1. Sign up or log in to **Render** (https://render.com).
2. Go to the dashboard and click **New** ➔ **Blueprint**.
3. Connect your GitHub account and select the `telugu-doc-portal` repository.
4. Render will automatically read `render.yaml` and prompt you to create:
   - A free PostgreSQL Database named `telugu-book-db`.
   - A Web Service named `telugu-book-portal`.
5. Click **Apply**.

Render will now provision the database and build the Python web container. On startup, the container will run `deploy_seed.py` which:
- Automatically initializes the database tables, indices, and trigram extensions.
- Ingests all 37 pages, 142 text blocks, and 18 image binary crops.

Once deployed, Render will provide a permanent public HTTPS URL (e.g. `https://telugu-book-portal.onrender.com`) that stays live 24/7.
