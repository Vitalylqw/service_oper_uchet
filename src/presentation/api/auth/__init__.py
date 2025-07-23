"""
Authentication and authorization module.

Contains JWT token management, password hashing, RBAC implementation,
and authentication dependencies for FastAPI endpoints.
"""

from .models import User, UserRole
from .security import create_access_token, get_current_user, verify_password

__all__ = ["User", "UserRole", "create_access_token", "get_current_user", "verify_password"]
