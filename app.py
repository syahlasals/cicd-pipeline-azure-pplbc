import os
import uuid
from flask import Flask, request, render_template, redirect, url_for
from azure.storage.blob import BlobServiceClient
import psycopg2
from dotenv import load_dotenv

# Load environment variables dari file .env
load_dotenv()

app = Flask(__name__)

# Konfigurasi dari .env
DB_HOST     = os.getenv("DB_HOST")
DB_NAME     = os.getenv("DB_NAME")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT     = os.getenv("DB_PORT", "5432")

AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
AZURE_CONTAINER_NAME    = os.getenv("AZURE_CONTAINER_NAME")

# Koneksi ke PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode="require"   # wajib untuk Azure PostgreSQL
    )
    return conn

# Route: Halaman Form
@app.route("/")
def index():
    return render_template("index.html")

# Route: Proses Submit Form
@app.route("/submit", methods=["POST"])
def submit():
    nama  = request.form.get("nama")
    email = request.form.get("email")
    file  = request.files.get("file")

    if not nama or not email or not file:
        return "Semua field wajib diisi!", 400

    # Upload file ke Azure Blob Storage
    try:
        # Buat nama file unik
        file_extension = os.path.splitext(file.filename)[1]
        blob_name = f"{uuid.uuid4()}{file_extension}"

        # Koneksi ke Azure Blob
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(
            container=AZURE_CONTAINER_NAME,
            blob=blob_name
        )

        # Upload file
        blob_client.upload_blob(
            file.read(),
            overwrite=True,
            content_type=file.content_type
        )
        # Buat URL publik file
        account_name = blob_service_client.account_name
        foto_url = f"https://{account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{blob_name}"

    except Exception as e:
        return f"Gagal upload ke Blob Storage: {str(e)}", 500

    # Simpan data ke PostgreSQL
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO pelamar (nama, email, ktp_url) VALUES (%s, %s, %s)",
            (nama, email, foto_url)
        )
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        return f"Gagal menyimpan ke database: {str(e)}", 500

    return render_template("success.html", nama=nama, email=email, foto_url=foto_url)


if __name__ == "__main__":
    app.run(debug=True)