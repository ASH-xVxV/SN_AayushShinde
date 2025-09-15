# src/server.py
from flask import Flask, request, jsonify
import os
import uuid
import time
from datetime import datetime
from access_control import check_access
from utils.encryption import decrypt_file  # decrypt_file will be implemented next

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))        # .../src
STORAGE_DIR = os.path.join(BASE_DIR, "storage")              # .../src/storage

ALLOWED_FOLDERS = {"docs", "media", "family", "guest"}

# In-memory guest store: guest_id -> expiry_timestamp (epoch)
guest_store = {}

def is_guest_valid(guest_id):
    expiry = guest_store.get(guest_id)
    if not expiry:
        return False
    if time.time() > expiry:
        # expired, remove
        guest_store.pop(guest_id, None)
        return False
    return True

def safe_join(base, *paths):
    """Return a normalized safe path and ensure it's inside base."""
    candidate = os.path.normpath(os.path.join(base, *paths))
    base_norm = os.path.normpath(base)
    return candidate if candidate.startswith(base_norm) else None

@app.route("/")
def index():
    return jsonify({
        "message": "Personal Home Cloud API",
        "routes": [
            "GET /list/<role>/<folder>?guest_id=...",
            "GET /file/<role>/<folder>/<filename>?guest_id=...",
            "POST /guest  {\"duration_minutes\":60}"
        ]
    })

@app.route("/guest", methods=["POST"])
def create_guest():
    """Create a temporary guest ID. JSON body: { "duration_minutes": 60 }"""
    data = request.get_json(silent=True) or {}
    duration = int(data.get("duration_minutes", 60))
    guest_id = str(uuid.uuid4())
    expiry = time.time() + duration * 60
    guest_store[guest_id] = expiry
    return jsonify({
        "guest_id": guest_id,
        "expires_at_utc": datetime.utcfromtimestamp(expiry).isoformat() + "Z"
    })

@app.route("/list/<role>/<folder>", methods=["GET"])
def list_files(role, folder):
    guest_id = request.args.get("guest_id")
    folder = folder.strip()
    if folder not in ALLOWED_FOLDERS:
        return jsonify({"error": "Unknown folder"}), 400

    # guest must provide valid guest_id
    if role == "guest":
        if not guest_id or not is_guest_valid(guest_id):
            return jsonify({"error": "Invalid or expired guest_id"}), 403

    # check RBAC (access_control.check_access should accept (role, folder, guest_id=None))
    if not check_access(role, folder, guest_id):
        return jsonify({"error": "Access denied"}), 403

    folder_path = os.path.join(STORAGE_DIR, folder)
    if not os.path.exists(folder_path):
        return jsonify({"error": "Folder not found"}), 404

    files = os.listdir(folder_path)
    return jsonify({"files": files})

@app.route("/file/<role>/<folder>/<path:filename>", methods=["GET"])
def get_file(role, folder, filename):
    guest_id = request.args.get("guest_id")
    folder = folder.strip()
    if folder not in ALLOWED_FOLDERS:
        return jsonify({"error": "Unknown folder"}), 400

    if role == "guest":
        if not guest_id or not is_guest_valid(guest_id):
            return jsonify({"error": "Invalid or expired guest_id"}), 403

    if not check_access(role, folder, guest_id):
        return jsonify({"error": "Access denied"}), 403

    folder_path = os.path.join(STORAGE_DIR, folder)
    target = safe_join(folder_path, filename)
    if not target:
        return jsonify({"error": "Invalid filename/path"}), 400
    if not os.path.exists(target):
        return jsonify({"error": "File not found"}), 404

    try:
        # if encrypted file (.enc) try to decrypt using utils.encryption.decrypt_file
        if filename.endswith(".enc"):
            content = decrypt_file(target)  # returns string
            return jsonify({"filename": filename, "content": content})
        # otherwise return text file content (utf-8)
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"filename": filename, "content": content})
    except Exception as e:
        return jsonify({"error": "Failed to read file", "detail": str(e)}), 500

@app.route("/guests", methods=["GET"])
def list_guests():
    now = time.time()
    active = {}
    for gid, exp in list(guest_store.items()):
        if exp > now:
            active[gid] = datetime.utcfromtimestamp(exp).isoformat() + "Z"
        else:
            guest_store.pop(gid, None)
    return jsonify(active)

if __name__ == "__main__":
    # debug mode is fine for the demo / test environment
    app.run(host="0.0.0.0", port=5000, debug=True)

