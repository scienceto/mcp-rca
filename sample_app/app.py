import uuid
from google.cloud import storage
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text

app = Flask(__name__)

# GCS Config
GCS_BUCKET_NAME = "YOUR_BUCKET_NAME"

# Database Config
DB_URL = "DRIVER://USERNAME:PASSWORD@HOST/DBNAME"
engine = create_engine(DB_URL)

# GCS Upload
def upload_to_gcs(file_obj, filename):
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_file(file_obj)
    return f"gs://{GCS_BUCKET_NAME}/{filename}"

# Dummy DB Load
def perform_dummy_sql_operations():
    with engine.connect() as conn:
        # Create temp table if not exists (note: TEMP TABLES are per-session)
        # and do dummy insert/update
        conn.execute(text("""
            CREATE TEMP TABLE IF NOT EXISTS temp_data (
                id SERIAL PRIMARY KEY,
                name TEXT
            );
        """))
        
        result = conn.execute(text("SELECT id FROM temp_data LIMIT 1;")).fetchone()
        if result:
            conn.execute(
                text("UPDATE temp_data SET name = :name WHERE id = :id"),
                {"name": "Updated_User", "id": result.id}
            )
        else:
            conn.execute(
                text("INSERT INTO temp_data (name) VALUES (:name)"),
                {"name": "Initial_User"}
            )

        count = conn.execute(text("SELECT COUNT(*) FROM temp_data;")).scalar()
        return count

@app.route("/", methods=["GET"])
def index():
    return '''
    <form method="post" action="/upload" enctype="multipart/form-data">
      <input type="file" name="file">
      <input type="submit" value="Upload">
    </form>
    '''

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = f"{uuid.uuid4()}_{file.filename}"
    gcs_path = upload_to_gcs(file, filename)

    row_count = perform_dummy_sql_operations()

    return jsonify({
        "message": "File uploaded successfully",
        "gcs_path": gcs_path,
        "dummy_sql_rows": row_count
    })

if __name__ == "__main__":
    app.run(debug=True)
