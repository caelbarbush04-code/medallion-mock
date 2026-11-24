from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
import datetime
import uuid
import os

app = Flask(__name__)
CORS(app)

# Simple in-memory data
API_KEYS = {"test-key-123": "Demo Company"}

jobs = {
    "J1001": {"job_number": "J1001", "builder": "ABC Homes", "lot": "12", "plan": "Plan A", "status": "Active"},
    "J1002": {"job_number": "J1002", "builder": "XYZ Builders", "lot": "45", "plan": "Plan B", "status": "Active"},
    "J1003": {"job_number": "J1003", "builder": "ABC Homes", "lot": "8", "plan": "Plan A", "status": "Active"},
}

parts = {
    "DRY-001": {"part_number": "DRY-001", "description": "1/2\" Drywall 4x8", "unit": "sheet", "cost": 12.50},
    "DRY-002": {"part_number": "DRY-002", "description": "5/8\" Drywall 4x8", "unit": "sheet", "cost": 14.75},
    "SCR-100": {"part_number": "SCR-100", "description": "Drywall Screws 1-1/4\"", "unit": "box", "cost": 8.25},
    "TAPE-50": {"part_number": "TAPE-50", "description": "Paper Tape 500'", "unit": "roll", "cost": 4.50},
    "COMP-200": {"part_number": "COMP-200", "description": "All Purpose Compound 5gal", "unit": "bucket", "cost": 18.00},
}

# Track material issues
material_issues = []

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
        if not key or key not in API_KEYS:
            return jsonify({"error": "Invalid or missing API key. Use header: x-api-key"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def home():
    return jsonify({
        "service": "Medallion Mock API",
        "version": "1.0",
        "message": "Use this to test material charging integrations",
        "endpoints": [
            "GET /api/v1/jobs",
            "GET /api/v1/parts",
            "POST /api/v1/jobs/<job_number>/materials",
            "GET /api/v1/materials/issues"
        ],
        "auth": "Header: x-api-key: test-key-123"
    })

@app.route("/api/v1/jobs", methods=["GET"])
@require_api_key
def get_jobs():
    return jsonify({
        "success": True,
        "jobs": list(jobs.values())
    })

@app.route("/api/v1/parts", methods=["GET"])
@require_api_key
def get_parts():
    return jsonify({
        "success": True,
        "parts": list(parts.values())
    })

# Accept any part number (for testing with real Austin Electric codes)
@app.route("/api/v1/jobs/<job_number>/materials", methods=["POST"])
@require_api_key
def charge_material(job_number):
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    part_number = data.get("part_number")
    quantity = data.get("quantity")
    description = data.get("description", "")
    notes = data.get("notes", "")

    if not part_number or quantity is None:
        return jsonify({"error": "part_number and quantity are required"}), 400

    try:
        qty = float(quantity)
        if qty <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "quantity must be a positive number"}), 400

    # Look up known part or accept any
    part_info = parts.get(part_number, {
        "description": description or f"Part {part_number}",
        "unit": "ea",
        "cost": 0.0
    })

    issue = {
        "id": str(uuid.uuid4())[:8],
        "job_number": job_number,
        "part_number": part_number,
        "description": part_info["description"],
        "quantity": qty,
        "unit": part_info.get("unit", "ea"),
        "unit_cost": part_info.get("cost", 0),
        "extended_cost": round(qty * part_info.get("cost", 0), 2),
        "notes": notes,
        "charged_at": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "Posted"
    }
    material_issues.append(issue)

    return jsonify({
        "success": True,
        "message": "Material charged to job successfully",
        "issue": issue
    }), 201

@app.route("/api/v1/materials/issues", methods=["GET"])
@require_api_key
def get_issues():
    return jsonify({
        "success": True,
        "count": len(material_issues),
        "issues": material_issues
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
