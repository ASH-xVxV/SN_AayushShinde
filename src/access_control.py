# src/access_control.py
"""
Simple Role-Based Access Control mapping.
This file defines which folders each role can access.
The server enforces guest expiry separately.
"""

role_access = {
    "self": ["docs", "media", "family", "guest"],
    "parent": ["docs", "family"],
    "sibling": ["media"],
    "guest": ["guest"]
}

def check_access(role: str, folder: str, guest_id: str = None) -> bool:
    """Return True if the given role is allowed to access the folder."""
    # normalize inputs
    role = (role or "").lower()
    folder = (folder or "").lower()
    allowed = role_access.get(role, [])
    return folder in allowed
