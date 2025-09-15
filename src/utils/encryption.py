# src/utils/encryption.py
from cryptography.fernet import Fernet
import os

# secret.key will be placed at src/secret.key (next to server.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../src
KEY_FILE = os.path.join(BASE_DIR, "secret.key")

def generate_key():
    """Create a new Fernet key and save it to src/secret.key (one-time)."""
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

def load_key():
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError("secret.key not found. Run generate_key() locally or place the key at src/secret.key")
    with open(KEY_FILE, "rb") as f:
        return f.read()

def encrypt_bytes(data: bytes) -> bytes:
    key = load_key()
    return Fernet(key).encrypt(data)

def decrypt_bytes(token: bytes) -> bytes:
    key = load_key()
    return Fernet(key).decrypt(token)

def encrypt_file(path: str) -> str:
    """Encrypt a file in-place: writes path + '.enc', returns new path."""
    with open(path, "rb") as f:
        data = f.read()
    token = encrypt_bytes(data)
    out = path + ".enc"
    with open(out, "wb") as f:
        f.write(token)
    return out

def decrypt_file(path: str) -> str:
    """Read encrypted file and return decrypted text (utf-8)."""
    with open(path, "rb") as f:
        token = f.read()
    data = decrypt_bytes(token)
    return data.decode("utf-8")
