import os
import sqlite3
import uuid
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

load_dotenv()

from decision_engine import get_cost_range, check_quote, repair_vs_replace, get_questions
from ai_layer import interpret_problem


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "fixwise.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


@app.context_processor
def inject_active_page():
    active = (
        "diagnose"
        if request.path in ("/", "/analyze")
        else "passport"
        if request.path == "/history"
        else ""
    )
    return {"active": active}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    device_type = request.form.get("device_type", "Laptop")
    brand = request.form.get("brand", "").strip()
    model = request.form.get("model", "").strip()
    problem_text = request.form.get("problem", "").strip()

    try:
        age = int(request.form.get("age", 0))
    except ValueError:
        age = 0

    quote_raw = request.form.get("quote", "").strip()
    quote = int(quote_raw) if quote_raw.isdigit() else None

    replacement_raw = request.form.get("replacement_value", "").strip()

    replacement_defaults = {
    "Laptop": 50000,
    "Phone": 25000,
    "Tablet": 25000,
    "TV": 50000,
    "Monitor": 25000,
    }

    replacement_value = (
    int(replacement_raw)
    if replacement_raw.isdigit()
    else replacement_defaults.get(device_type, 35000)
    )

    if not problem_text:
        return render_template(
            "index.html",
            error="Please describe the problem before running a diagnosis."
        )

    if not brand or not model:
        return render_template(
            "index.html",
            error="Please enter the brand and model of your device."
        )

    # Handle optional image upload.
    image = request.files.get("problem_image")
    image_path = None

    if image and image.filename:
        if not allowed_image(image.filename):
            return render_template(
                "index.html",
                error="Please upload a PNG, JPG, JPEG, or WEBP image."
            )

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        safe_filename = secure_filename(image.filename)

        if not safe_filename:
            return render_template(
                "index.html",
                error="The selected image could not be read. Please choose the image again."
            )

        extension = safe_filename.rsplit(".", 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{extension}"

        image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        image.save(image_path)

    ai_result = interpret_problem(
        problem_text,
        device_type,
        brand,
        model,
        image_path
    )

    category = ai_result["category"]
    confidence = ai_result["confidence"]
    safety_flag = ai_result["safety_flag"]
    explanation = ai_result.get("explanation", "")

    low, high, repairability, life_years = get_cost_range(
        device_type,
        category
    )

    quote_status, quote_message = check_quote(
        quote,
        low,
        high
    )

    recommendation, rec_message = repair_vs_replace(
        age,
        low,
        high,
        replacement_value,
        category,
        confidence,
        safety_flag
    )

    questions = get_questions(category)

    report = {
        "device_type": device_type,
        "brand": brand,
        "model": model,
        "age": age,
        "problem_text": problem_text,
        "quote": quote,
        "replacement_value": replacement_value,
        "category": category.replace("_", " "),
        "confidence": confidence,
        "safety_flag": safety_flag,
        "explanation": explanation,
        "low": low,
        "high": high,
        "repairability": repairability,
        "life_years": life_years,
        "quote_status": quote_status,
        "quote_message": quote_message,
        "recommendation": recommendation,
        "rec_message": rec_message,
        "questions": questions,
    }

    conn = get_db()

    conn.execute(
        """INSERT INTO reports
           (device_type, brand, model, age, problem_text, quote,
            category, confidence, recommendation, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            device_type,
            brand,
            model,
            age,
            problem_text,
            quote,
            category,
            confidence,
            recommendation,
            datetime.utcnow().isoformat(),
        ),
    )

    conn.commit()
    conn.close()

    return render_template("result.html", r=report)


@app.route("/history")
def history():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM reports ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("history.html", rows=rows)


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("Database not found — run 'python init_db.py' first.")

    app.run(debug=True, port=5000)