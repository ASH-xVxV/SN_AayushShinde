# access_control.py
from functools import wraps
from flask import request, abort

# Simulate a user database (in a real project, use a real DB like SQLite)
USERS = {
    "admin": {"password": "pbkdf2:sha256:150000$...", "role": "admin"},
    "parent": {"password": "pbkdf2:sha256:150000$...", "role": "family"},
    "guest_user": {"password": "pbkdf2:sha256:150000$...", "role": "guest"}
}

# Define what each role can access
ROLE_PERMISSIONS = {
    "admin": ["admin_panel", "family", "guest", "logs"], # Can access everything
    "family": ["family", "guest"], # Can access family and guest docs
    "guest": ["guest"] # Can only access the guest folder
}

def hash_password(password):
    """Hash a password for storing."""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)

def verify_password(stored_hash, provided_password):
    """Verify a stored password against one provided by user."""
    from werkzeug.security import check_password_hash
    return check_password_hash(stored_hash, provided_password)

# Initialize the user DB with hashed passwords
# In a real app, you'd run this once separately.
if __name__ == "__init__":
    USERS["admin"]["password"] = hash_password("admin_secret")
    USERS["parent"]["password"] = hash_password("family_secret")
    USERS["guest_user"]["password"] = hash_password("guest_secret")

def check_access(role, requested_path):
    """Check if a role has permission to access a path."""
    for allowed_folder in ROLE_PERMISSIONS.get(role, []):
        if requested_path.startswith(f'/{allowed_folder}'):
            return True
    return False

def requires_auth(role_required=None):
    """Decorator to enforce authentication and authorization on a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get the username and password from the request's authorization header
            auth = request.authorization
            if not auth or not verify_password(USERS.get(auth.username, {}).get('password'), auth.password):
                # Return a 401 Unauthorized error if login fails
                return abort(401, "Invalid credentials. Please log in.")
            
            user_role = USERS[auth.username]['role']
            
            # Check if the user's role is allowed to access the route
            if role_required and user_role != role_required:
                return abort(403, "You do not have permission to access this resource.")
            
            # Check if the user's role is allowed to access the specific file path
            if not check_access(user_role, request.path):
                return abort(403, "Access denied to this path.")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
