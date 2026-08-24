"""
Social Media Content Analyzer
Flask web app: upload a PDF or image of a social media post,
extract its text (PDF parsing / OCR), and get engagement-improvement
suggestions.
"""
import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from extractor import extract_text
from analyzer import analyze_content

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Please upload a PDF, PNG, or JPG."}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        extracted_text = extract_text(filepath)
        if not extracted_text or not extracted_text.strip():
            return jsonify({
                "error": "Could not extract any text from this file. "
                         "Try a clearer image or a text-based PDF."
            }), 422

        suggestions = analyze_content(extracted_text)

        return jsonify({
            "filename": filename,
            "extracted_text": extracted_text,
            "analysis": suggestions,
        })
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the UI
        return jsonify({"error": f"Failed to process file: {exc}"}), 500
    finally:
        # Clean up the uploaded file; we don't need to persist it.
        if os.path.exists(filepath):
            os.remove(filepath)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
