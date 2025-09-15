# server.py
from flask import Flask, send_file, request, abort
from access_control import requires_auth
from encryption import decrypt_file
import os
from io import BytesIO

app = Flask(__name__)
BASE_STORAGE_PATH = "storage"

@app.route('/')
def home():
    return "Welcome to the Secure Home Cloud. Please log in."

@app.route('/<path:folder>/<filename>')
@requires_auth() # This decorator now handles both auth and path permission
def serve_file(folder, filename):
    """Main route to serve files. Access control is enforced by the decorator."""
    file_path = os.path.join(BASE_STORAGE_PATH, folder, filename)
    
    # Check if the file exists
    if not os.path.isfile(file_path):
        return abort(404, "File not found.")
    
    try:
        # Decrypt the file on the fly and serve it
        decrypted_data = decrypt_file(file_path)
        return send_file(
            BytesIO(decrypted_data),
            as_attachment=False, # Set to True to force download
            download_name=filename # Serve it with the original name
        )
    except Exception as e:
        return abort(500, f"Error retrieving file: {str(e)}")

if __name__ == '__main__':
    # Before starting, encrypt all files in the storage directory
    from encryption import encrypt_storage
    print("Encrypting files at rest...")
    encrypt_storage(BASE_STORAGE_PATH)
    print("Starting server...")
    app.run(host='0.0.0.0', port=5000, ssl_context='adhoc') # adhoc for self-signed HTTPS
