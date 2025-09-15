# encryption.py
from cryptography.fernet import Fernet
import os

# Key should be loaded from a very secure location (env variable) in production!
# Generate a key: `key = Fernet.generate_key()`
KEY = os.getenv('ENCRYPTION_KEY', 'your_super_secret_key_here') 
cipher_suite = Fernet(KEY)

def encrypt_file(input_path, output_path):
    """Reads a file, encrypts its contents, and writes it."""
    with open(input_path, 'rb') as file:
        file_data = file.read()
    encrypted_data = cipher_suite.encrypt(file_data)
    with open(output_path, 'wb') as file:
        file.write(encrypted_data)

def decrypt_file(input_path):
    """Reads an encrypted file and returns the decrypted data."""
    with open(input_path, 'rb') as file:
        encrypted_data = file.read()
    try:
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        return decrypted_data
    except Exception as e:
        raise Exception("Failed to decrypt file. It may be corrupted or the key is wrong.") from e

# Optional: Function to encrypt all files in a directory at startup
def encrypt_storage(base_path):
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if not file.endswith('.encrypted'): # Avoid double-encrypting
                file_path = os.path.join(root, file)
                encrypt_file(file_path, file_path + '.encrypted')
                os.remove(file_path) # Delete the original plain text file
