"""
The only job of this layer is to read the user's free-text description and
map it to one of the fixed categories the decision engine understands.
It never returns a price — the repair-cost database and decision_engine.py
are the only source of pricing.

Tries Gemini first, then Anthropic if configured, then falls back to
simple keyword matching so the app always works.
"""

import json
import os
import re
import base64
import requests

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-3.6-flash:generateContent"
)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

ALLOWED_CATEGORIES = {
    "battery",
    "overheating",
    "screen",
    "motherboard_power",
    "keyboard",
    "storage_ram",
    "liquid_damage",
    "charging",
    "power",
    "other",
}


def _build_prompt(problem_text, device_type, brand="", model=""):
    return f"""
You are the diagnosis layer of FixWise, a consumer repair decision tool.

Device type: {device_type}
Brand: {brand or "Unknown"}
Model: {model or "Unknown"}

Classify the user's device problem into exactly one of these categories:

battery
overheating
screen
motherboard_power
keyboard
storage_ram
liquid_damage
charging
power
other

Return ONLY valid JSON in this exact format:

{{
  "category": "battery",
  "confidence": "High",
  "safety_flag": false,
  "explanation": "Short explanation of why the problem matches the category."
}}

Rules:
- confidence must be High, Medium, or Low.
- safety_flag must be true or false.
- Do not invent a diagnosis beyond the available evidence.
- If the image or description is insufficient, use Low confidence.
- For electrical, liquid, swollen-battery, burning, smoke, or other potentially hazardous situations, set safety_flag to true.
- Use "charging" when the main problem is that the device does not charge,
  charges intermittently, charges slowly, or has a charging-port/cable issue.
- Use "battery" when the description specifically indicates battery
  degradation, rapid battery drain, swelling, or battery failure.
- Keep the explanation short.

User's problem:
{problem_text}
""".strip()


def _encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _image_mime_type(image_path):
    extension = os.path.splitext(image_path)[1].lower()

    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    return mime_types.get(extension, "image/jpeg")


def _call_gemini(
    problem_text,
    device_type,
    brand="",
    model="",
    image_path=None,
):
    if not GEMINI_API_KEY:
        return None

    prompt = _build_prompt(
        problem_text,
        device_type,
        brand,
        model,
    )

    parts = [{"text": prompt}]

    if image_path and os.path.exists(image_path):
        parts.append(
            {
                "inline_data": {
                    "mime_type": _image_mime_type(image_path),
                    "data": _encode_image(image_path),
                }
            }
        )

    payload = {
        "contents": [
            {
                "parts": parts
            }
        ]
    }

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            print("Gemini error:", response.status_code, response.text)
            return None

        data = response.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]

        text = re.sub(r"^```json\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text)

        result = json.loads(text)

        category = result.get("category", "other")
        confidence = result.get("confidence", "Low")
        safety_flag = result.get("safety_flag", False)
        explanation = result.get("explanation", "")

        if category not in ALLOWED_CATEGORIES:
            category = "other"

        if confidence not in {"High", "Medium", "Low"}:
            confidence = "Low"

        if not isinstance(safety_flag, bool):
            safety_flag = False

        return {
            "category": category,
            "confidence": confidence,
            "safety_flag": safety_flag,
            "explanation": explanation,
        }

    except Exception as e:
        print("Gemini exception:", e)
        return None


def _fallback_categorize(problem_text, device_type):
    text = problem_text.lower()

    if any(word in text for word in [
        "charging",
        "charge",
        "charger",
        "charging port",
        "charging cable",
        "not charging",
        "won't charge",
        "doesn't charge",
        "slow charging",
        "charges slowly",
        "intermittent charging",
    ]):
        return {
            "category": "charging",
            "confidence": "Medium",
            "safety_flag": False,
            "explanation": (
                f"The {device_type.lower()} problem description "
                "suggests a charging-related issue."
            ),
        }

    if any(word in text for word in [
        "battery",
        "drain",
        "draining",
        "battery life",
        "battery health",
        "swollen battery",
        "battery failure",
    ]):
        return {
            "category": "battery",
            "confidence": "Medium",
            "safety_flag": "swollen" in text,
            "explanation": (
                f"The {device_type.lower()} problem description "
                "suggests a battery-related issue."
            ),
        }

    if any(word in text for word in [
        "overheat",
        "overheating",
        "hot",
        "heat",
    ]):
        return {
            "category": "overheating",
            "confidence": "Medium",
            "safety_flag": False,
            "explanation": (
                f"The {device_type.lower()} is described as "
                "running unusually hot."
            ),
        }

    if any(word in text for word in [
        "screen",
        "display",
        "crack",
        "touch",
    ]):
        return {
            "category": "screen",
            "confidence": "Medium",
            "safety_flag": False,
            "explanation": (
                f"The description points to a display or screen "
                f"problem with the {device_type.lower()}."
            ),
        }

    if any(word in text for word in [
        "liquid",
        "water",
        "spill",
        "wet",
    ]):
        return {
            "category": "liquid_damage",
            "confidence": "Medium",
            "safety_flag": True,
            "explanation": (
                "The description suggests possible liquid damage, "
                "which requires physical inspection."
            ),
        }

    if any(word in text for word in [
        "power",
        "won't turn on",
        "doesn't turn on",
        "not switching on",
        "dead",
    ]):
        return {
            "category": "power",
            "confidence": "Medium",
            "safety_flag": True,
            "explanation": (
                f"The description suggests a power-related issue "
                f"with the {device_type.lower()}."
            ),
        }

    return {
        "category": "other",
        "confidence": "Low",
        "safety_flag": False,
        "explanation": (
            "The available description is not specific enough "
            "to confidently classify the problem."
        ),
    }


def interpret_problem(
    problem_text,
    device_type="Laptop",
    brand="",
    model="",
    image_path=None,
):
    result = _call_gemini(
        problem_text,
        device_type,
        brand,
        model,
        image_path,
    )

    if result:
        return result

    return _fallback_categorize(
        problem_text,
        device_type,
    )